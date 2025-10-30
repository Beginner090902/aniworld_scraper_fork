from flask import Flask, request, jsonify, render_template, make_response, Response, stream_with_context
import subprocess
import threading
import os
import re
import time
from flask_socketio import SocketIO, emit
import logging
from src.custom_logging import init_logger_socketio, setup_logger

import queue  # neu: für SSE-subscriber Queues

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Logger mit WebSocket initialisieren
init_logger_socketio(socketio)

# Logger für diese App erstellen
logger = setup_logger('flask_app')

# --- SSE subscriber-Verwaltung ---
_subscribers = []
_sub_lock = threading.Lock()

def subscribe():
    """Erzeuge eine neue Queue für einen neuen SSE-Client und füge sie zur Liste hinzu."""
    q = queue.Queue()
    with _sub_lock:
        _subscribers.append(q)
    return q

def unsubscribe(q):
    """Entferne die Queue eines Clients (z. B. beim Disconnect)."""
    with _sub_lock:
        try:
            _subscribers.remove(q)
        except ValueError:
            pass

def broadcast_log(msg):
    """Schicke msg an alle aktiven Subscriber (non-blocking)."""
    with _sub_lock:
        for q in list(_subscribers):
            try:
                q.put_nowait(msg)
            except queue.Full:
                # falls Queue voll ist -> überspringen (oder evtl. älteste verworfen)
                pass

# ----------------------------------------------------

def _sanitize_name(name, max_length=200):
    if not isinstance(name, str):
        raise ValueError("Invalid name: not a string")
    name = name.strip()
    if not name:
        raise ValueError("Invalid name: empty after stripping")
    if len(name) > max_length:
        raise ValueError(f"Invalid name: exceeds max length of {max_length}")
    sanitized = re.sub(r"[^A-Za-z0-9 \-_.()]+", "_", name)
    sanitized = re.sub(r"\s+", " ", sanitized)
    return sanitized


def validate_and_sanitize_form(form):
    allowed_types = {'anime': 'anime', 'movie': 'movie', 'series': 'series'}
    allowed_langs = {'deutsch': 'Deutsch', 'english': 'English', 'japanese': 'Japanese'}
    allowed_modes = {'series': 'Series', 'movie': 'Movie'}
    allowed_providers = {'voe': 'VOE', 'streamtape': 'Streamtape', 'vidoza': 'Vidoza'}

    raw_type = form.get('type_of_media', '')
    raw_name = form.get('name', '')
    raw_lang = form.get('language', '')
    raw_mode = form.get('dlMode', '')
    raw_provider = form.get('cliProvider', '')

    t = str(raw_type).strip().lower()
    if t in allowed_types:
        media_type = allowed_types[t]
    else:
        media_type = 'anime'

    l = str(raw_lang).strip().lower()
    language = allowed_langs.get(l, 'Deutsch')

    m = str(raw_mode).strip().lower()
    dl_mode = allowed_modes.get(m, 'Series')

    p = str(raw_provider).strip().lower()
    provider = allowed_providers.get(p, 'VOE')

    try:
        name = _sanitize_name(str(raw_name))
    except ValueError as e:
        raise ValueError(f"Invalid 'name' field: {e}")

    return {
        'type_of_media': media_type,
        'name': name,
        'language': language,
        'dlMode': dl_mode,
        'cliProvider': provider,
    }


def run_download_script(sanitized_data):
    """Startet das Download-Skript mit validated/sanitized arguments und broadcastet live Logs."""
    try:
        cmd = [
            'python3', 'py_main.py',
            '--type', str(sanitized_data.get('type_of_media', 'anime')),
            '--name', str(sanitized_data.get('name', 'Name-Goes-Here')),
            '--lang', str(sanitized_data.get('language', 'Deutsch')),
            '--dl-mode', str(sanitized_data.get('dlMode', 'Series')),
            '--provider', str(sanitized_data.get('cliProvider', 'VOE'))
        ]

        logger.info(f"🔧 Starte Download: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,           # liefert str statt bytes
            bufsize=1,
            universal_newlines=True
        )

        # Live-Output lesen und als Log senden (und an SSE-Clients broadcasten)
        for line in iter(process.stdout.readline, ''):
            if line is None:
                break
            text = line.rstrip('\n')
            if text.strip():
                logger.info(f"[PY_MAIN] {text}")
                broadcast_log(text)   # <-- hier wird die gelesene Zeile an alle SSE-Clients geschickt

        # Auf Prozess-Ende warten
        returncode = process.wait()

        if returncode == 0:
            logger.info("✅ Download erfolgreich abgeschlossen")
            broadcast_log("✅ Download erfolgreich abgeschlossen")
        else:
            logger.error(f"❌ Download mit Fehlercode {returncode} beendet")
            broadcast_log(f"❌ Download mit Fehlercode {returncode} beendet")

    except Exception as e:
        logger.error(f"❌ Fehler beim Download: {str(e)}")
        broadcast_log(f"❌ Fehler beim Download: {str(e)}")


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return make_response(render_template('index.html'))
    elif request.method == 'POST':
        print("=== FORMULAR DATEN EMPFANGEN ===")
        for key, value in request.form.items():
            print(f"{key}: {value}")
        print("=================================")

        try:
            sanitized = validate_and_sanitize_form(request.form)
        except ValueError as e:
            print(f"❌ Formular Validierungsfehler: {e}")
            return render_template('index.html', message="Ungültige Eingabe. Bitte überprüfen Sie Ihre Daten.")

        thread = threading.Thread(target=run_download_script, args=(sanitized,))
        thread.daemon = True
        thread.start()

        return render_template('index.html', message="Download gestartet!")


@app.route('/log_stream')
def log_stream():
    """
    SSE-Endpunkt: bei jeder Verbindung bekommt der Client seine eigene Queue.
    Server schreibt in diese Queues via broadcast_log(...)
    """
    client_q = subscribe()

    def generate():
        try:
            # blockiert, bis neue Nachricht in client_q ist
            while True:
                msg = client_q.get()
                # SSE-Format: data: <text>\n\n
                yield f"data: {msg}\n\n"
        except GeneratorExit:
            # Client hat sich getrennt (oder andere Abbruchgründe)
            pass
        finally:
            # wichtig: aufräumen
            unsubscribe(client_q)

    headers = {"Cache-Control": "no-cache"}
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers=headers)


if __name__ == '__main__':
    # Debug-ReLoader stört SSE manchmal (doppelte Prozesse), deshalb debug=False oder use_reloader=False
    app.run(host='127.0.0.1', port=5000, threaded=True, debug=False)
