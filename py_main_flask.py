from flask import Flask, render_template, request, jsonify
import os


app = Flask(__name__)


@app.route('/')
def home():
    return render_template('home.html')



@app.route('/start-download', methods=['POST'])
def start_download():
    try:
        # JSON-Daten aus dem Request-Body lesen
        config_data = request.get_json()
        
        # Überprüfen, ob Daten empfangen wurden
        if not config_data:
            return jsonify({'error': 'No JSON data received'}), 400
        
        # Hier kannst du auf die Konfigurationsdaten zugreifen
        type_of_media = config_data.get('type_of_media', 'anime')
        name = config_data.get('name', 'Name-Goes-Here')
        language = config_data.get('language', 'Deutsch')
        dlMode = config_data.get('dlMode', 'Series')
        cliProvider = config_data.get('cliProvider', 'VOE')
        
        # Beispiel: Daten verarbeiten
        print(f"Download gestartet für: {name}")
        print(f"Typ: {type_of_media}, Sprache: {language}")

        cmd  = f"python3 py_main.py --type {type_of_media} --name {name} --lang {language} --dl-mode {dlMode} --provider {cliProvider}"
        os.system(cmd)
        
        # Hier deinen Download-Code einfügen
        # run_download_script(config_data)
        
        # Erfolgsantwort zurückgeben
        return jsonify({
            'message': 'Download erfolgreich gestartet',
            'received_config': config_data
        }), 200
        
    except Exception as e:
        print(f"Fehler: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)