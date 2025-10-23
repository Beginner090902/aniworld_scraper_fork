FROM python:3.12.12-slim

# System-Abhängigkeiten installieren
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Arbeitsverzeichnis erstellen
WORKDIR /app

# Dateien kopieren
COPY . /app

# Python Abhängigkeiten installieren
RUN pip install --no-cache-dir -r requirements.txt

# Umgebungsvariable für Flask setzen
ENV FLASK_APP=py_main_flask.py
ENV FLASK_ENV=production

# Port freigeben
EXPOSE 5000

# Flask Server starten (wird beim Container-Start ausgeführt)
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]