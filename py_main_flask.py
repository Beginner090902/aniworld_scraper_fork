from flask import Flask, request, jsonify, render_template, make_response, Response, stream_with_context, redirect, url_for, flash
import json
import subprocess
import threading
import os
import re
import signal
import time
from flask_socketio import SocketIO, emit
import logging
from src.custom_logging import init_logger_socketio, setup_logger

import queue  # neu: für SSE-subscriber Queues

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-for-local')  # für Produktion: echte geheime Variable
socketio = SocketIO(app, cors_allowed_origins="*")

# Logger mit WebSocket initialisieren
init_logger_socketio(socketio)

# Logger für diese App erstellen
logger = setup_logger('flask_logger')
formatter = logging.Formatter('%(message)s')

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

_LEVEL_RE = re.compile(r'\b(DEBUG|INFO|WARNING|ERROR|CRITICAL|LOADING|SUCCESS)\b', re.IGNORECASE)

def broadcast_log(msg, level=None):
    """Schicke msg an alle aktiven Subscriber; splitte bei neuen Zeilen und ermittle Level.
       level: optionaler Default-Level (z.B. 'INFO')
    """
    if msg is None:
        return

    # Falls bytes -> decode
    if isinstance(msg, bytes):
        try:
            msg = msg.decode('utf-8', errors='replace')
        except Exception:
            msg = str(msg)

    # splitte in einzelne physische Zeilen
    lines = msg.splitlines() or ['']

    with _sub_lock:
        for q in list(_subscribers):
            for line in lines:
                # versuche Level in der Zeile zu finden
                found = _LEVEL_RE.search(line)
                if found:
                    detected_level = found.group(1).upper()
                else:
                    detected_level = (level.upper() if isinstance(level, str) else None) or 'INFO'

                try:
                    # wir speichern tuple (text, level) - clientseitig erwarten wir plain text,level
                    q.put_nowait((line, detected_level))
                except queue.Full:
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


# globales Tracking
current_process = None
current_process_lock = threading.Lock()

def run_download_script(sanitized_data):
    global current_process
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
        broadcast_log(f"🔧 Starte Download: {' '.join(cmd)}")

        # Plattform-spezifische Optionen: neue Prozessgruppe erstellen
        popen_kwargs = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        if os.name == 'nt':
            # Windows
            popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            # Unix (start new session => eigene PGID)
            popen_kwargs['start_new_session'] = True

        process = subprocess.Popen(cmd, **popen_kwargs)

        # setze globalen current_process (thread-sicher)
        with current_process_lock:
            current_process = process

        # Live-Output lesen
        for line in iter(process.stdout.readline, ''):
            if line is None:
                break
            text = line.rstrip('\n').strip()
            if not text:
                continue  # leere Zeilen überspringen

            # Wenn Zeile nur "[PY_MAIN]" enthält -> überspringen
            if text == "[PY_MAIN]" or text.startswith("[PY_MAIN]") and len(text) < 15:
                continue

            logger.info(f"{text}")
            broadcast_log(text)

        # warten
        returncode = process.wait()

        if returncode == 0:
            logger.info("✅ Download erfolgreich abgeschlossen")
            broadcast_log("✅ Download erfolgreich abgeschlossen")
        else:
            logger.error(f"❌ Download mit Fehlercode {returncode} beendet")
            broadcast_log(f"❌ Download mit Fehlercode {returncode} beendet", level='ERROR')


    except Exception as e:
        logger.error(f"❌ Fehler beim Download: {str(e)}")
        broadcast_log(f"❌ Fehler beim Download: {str(e)}")

    finally:
        # clear current process
        with current_process_lock:
            # falls process wurde ersetzt/ausserhalb verändert, nur clear wenn identisch
            try:
                if current_process is process:
                    current_process = None
            except NameError:
                current_process = None


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
            flash("Ungültige Eingabe. Bitte überprüfen Sie Ihre Daten.", "error")
            return redirect(url_for('index'))

        # Hintergrund-Task mit socketio starten (robuster als threading.Thread)
        socketio.start_background_task(run_download_script, sanitized)

        flash("Download gestartet!", "success")
        # Redirect auf die GET-Version der Index-Seite (PRG)
        return redirect(url_for('index'))


@app.route('/settings', methods=['GET'])
def settings():
    return make_response(render_template('settings.html'))

@app.route('/log_stream')
def log_stream():
    client_q = subscribe()

    def generate():
        try:
            while True:
                item = client_q.get()
                if item is None:
                    break
                # item ist (line, level)
                if isinstance(item, tuple) and len(item) == 2:
                    text, lvl = item
                else:
                    text, lvl = str(item), 'INFO'
                payload = json.dumps({'text': text, 'level': lvl})
                yield f"data: {payload}\n\n"
        except GeneratorExit:
            pass
        finally:
            unsubscribe(client_q)

    headers = {"Cache-Control": "no-cache"}
    return Response(stream_with_context(generate()), mimetype='text/event-stream', headers=headers)

@app.route('/stop', methods=['POST'])
def stop_current_process():
    """Versucht das aktuell laufende Programm zu stoppen."""
    global current_process
    with current_process_lock:
        p = current_process

    if p is None or p.poll() is not None:
        # kein laufender Prozess
        return jsonify({'status': 'no_process', 'message': 'Kein laufender Prozess'}), 400

    try:
        broadcast_log("⏹ Stop-Anfrage erhalten. Stoppe Prozess...")
        logger.info("Stop-Anfrage erhalten. Stoppe Prozess...")

        # Versuche sauberes Signal
        if os.name == 'nt':
            try:
                # send CTRL_BREAK to the process group (works when created with CREATE_NEW_PROCESS_GROUP)
                p.send_signal(signal.CTRL_BREAK_EVENT)
            except Exception:
                try:
                    p.terminate()
                except Exception:
                    pass
        else:
            try:
                # send SIGINT to process group
                os.killpg(os.getpgid(p.pid), signal.SIGINT)
            except Exception:
                try:
                    p.terminate()
                except Exception:
                    pass

        # Warte kurz auf beendigung
        try:
            p.wait(timeout=5)
        except Exception:
            # falls noch alive -> kill
            try:
                p.kill()
            except Exception:
                pass
            try:
                p.wait(timeout=2)
            except Exception:
                pass

        broadcast_log("⏹ Prozess gestoppt")
        logger.info("Prozess gestoppt")

        # sicherheitshalber clearen
        with current_process_lock:
            if current_process is p:
                current_process = None

        return jsonify({'status': 'stopped', 'message': 'Prozess gestoppt'}), 200

    except Exception as e:
        logger.exception("Fehler beim Stoppen des Prozesses")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@socketio.on('connect')
def on_connect():
    logger.info(f"Client connected: {request.sid}")
    if app.debug:
        socketio.emit('log_output', {'data': 'Connected to server', 'level': 'INFO'})


if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5000, debug=False)

