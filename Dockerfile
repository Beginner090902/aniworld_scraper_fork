FROM python:3.12.12-slim

# (1) Erstelle einen User mit UID/GID 1000
RUN groupadd -g 1000 appgroup \
    && useradd -u 1000 -g appgroup -m appuser

WORKDIR /app

# (2) Kopiere Dateien und setze Ownership
COPY --chown=appuser:appgroup . /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

ENV FLASK_APP=py_main_flask.py
ENV FLASK_DEBUG=0

EXPOSE 5000

# (3) Wechsle zum nicht-root Nutzer
USER appuser:appgroup

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
