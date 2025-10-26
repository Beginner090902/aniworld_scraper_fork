from flask import Flask, request, jsonify, render_template, make_response
import subprocess
import threading
import os

app = Flask(__name__)

def run_download_script(form_data):
    """Startet das Download-Skript in einem separaten Thread"""
    try:
        cmd = [
            'python3', 'py_main.py',
            '--type', form_data.get('type_of_media', 'anime'),
            '--name', form_data.get('name', 'Name-Goes-Here'),
            '--lang', form_data.get('language', 'Deutsch'),
            '--dl-mode', form_data.get('dlMode', 'Series'),
            '--provider', form_data.get('cliProvider', 'VOE')
        ]
        
        print(f"🔧 Starte Download: {' '.join(cmd)}")
        
        # Skript starten
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(f"✅ Download beendet mit Code: {result.returncode}")
        if result.stdout:
            print(f"📄 Output: {result.stdout}")
        if result.stderr:
            print(f"❌ Errors: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Fehler beim Download: {str(e)}")

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
        
        # Download in separatem Thread starten
        thread = threading.Thread(target=run_download_script, args=(request.form,))
        thread.daemon = True
        thread.start()

        start_befehlt = 'python3 py_main.py --type {} --name {} --lang {} --dl-mode {} --provider {}'.format(
            request.form.get('type_of_media', 'anime'),
            request.form.get('name', 'Name-Goes-Here'),
            request.form.get('language', 'Deutsch'),
            request.form.get('dlMode', 'Series'),
            request.form.get('cliProvider', 'VOE')
        )
        print(f"🔧 Startbefehl: {start_befehlt}")
        os.system(start_befehlt)
        return render_template('index.html', message="Download gestartet!")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)