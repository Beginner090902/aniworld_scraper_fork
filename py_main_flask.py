from flask import Flask, request, jsonify, render_template, make_response
import subprocess
import threading
import os
import re

app = Flask(__name__)

def _sanitize_name(name, max_length=200):
    if not isinstance(name, str):
        raise ValueError("Invalid name: not a string")
    name = name.strip()
    if not name:
        raise ValueError("Invalid name: empty after stripping")
    if len(name) > max_length:
        raise ValueError(f"Invalid name: exceeds max length of {max_length}")
    # Allow letters, numbers, spaces, dash, underscore, parentheses and dots.
    # Replace other characters with an underscore to avoid shell/control chars.
    sanitized = re.sub(r"[^A-Za-z0-9 \-_.()]+", "_", name)
    # collapse multiple spaces
    sanitized = re.sub(r"\s+", " ", sanitized)
    return sanitized


def validate_and_sanitize_form(form):
    """Validate form values and return a sanitized dict or raise ValueError.

    Accepted values are matched case-insensitively and mapped to canonical
    allowed values. Raises ValueError if validation fails.
    """
    allowed_types = {'anime': 'anime', 'movie': 'movie', 'series': 'series'}
    allowed_langs = {'deutsch': 'Deutsch', 'english': 'English', 'japanese': 'Japanese'}
    allowed_modes = {'series': 'Series', 'movie': 'Movie'}
    allowed_providers = {'voe': 'VOE', 'streamtape': 'Streamtape', 'vidoza': 'Vidoza'}

    # Extract raw values and coerce to strings where appropriate
    raw_type = form.get('type_of_media', '')
    raw_name = form.get('name', '')
    raw_lang = form.get('language', '')
    raw_mode = form.get('dlMode', '')
    raw_provider = form.get('cliProvider', '')

    # Normalize & validate
    t = str(raw_type).strip().lower()
    if t in allowed_types:
        media_type = allowed_types[t]
    else:
        media_type = 'anime'  # safe default

    l = str(raw_lang).strip().lower()
    language = allowed_langs.get(l, 'Deutsch')

    m = str(raw_mode).strip().lower()
    dl_mode = allowed_modes.get(m, 'Series')

    p = str(raw_provider).strip().lower()
    provider = allowed_providers.get(p, 'VOE')

    # Validate and sanitize name
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
    """Startet das Download-Skript mit validated/sanitized arguments.

    Expects a dict as returned by validate_and_sanitize_form.
    """
    try:
        cmd = [
            'python3', 'py_main.py',
            '--type', str(sanitized_data.get('type_of_media', 'anime')),
            '--name', str(sanitized_data.get('name', 'Name-Goes-Here')),
            '--lang', str(sanitized_data.get('language', 'Deutsch')),
            '--dl-mode', str(sanitized_data.get('dlMode', 'Series')),
            '--provider', str(sanitized_data.get('cliProvider', 'VOE'))
        ]

        print(f"🔧 Starte Download: {' '.join(cmd)}")

        # Skript starten
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60*60*24*2)
        print(f"✅ Download beendet mit Code: {result.returncode}")
        if result.stdout:
            print(f"📄 Output: {result.stdout}")
        if result.stderr:
            print(f"❌ Errors: {result.stderr}")

    except subprocess.TimeoutExpired:
        print(f"❌ Download timeout exceeded")
    except (subprocess.SubprocessError, OSError) as e:
        print(f"❌ Fehler beim Download: {str(e)}")
    except Exception as e:
        print(f"❌ Unerwarteter Fehler: {str(e)}")
        raise  # Re-raise unexpected exceptions for visibility

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return make_response(render_template('index.html'))
    elif request.method == 'POST':
        # Formulardaten auslesen
        print("=== FORMULAR DATEN EMPFANGEN ===")
        for key, value in request.form.items():
            print(f"{key}: {value}")
        print("=================================")
        
        # Validate form and start download in separate thread
        try:
            sanitized = validate_and_sanitize_form(request.form)
        except ValueError as e:
            print(f"❌ Formular Validierungsfehler: {e}")
            return render_template('index.html', message="Ungültige Eingabe. Bitte überprüfen Sie Ihre Daten.")

        thread = threading.Thread(target=run_download_script, args=(sanitized,))
        thread.daemon = True
        thread.start()

        return render_template('index.html', message="Download gestartet!")

if __name__ == '__main__':
    app.run(debug=False)