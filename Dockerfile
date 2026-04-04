FROM python:3.11.15-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1


WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*


ENV FLASK_APP=py_main_flask.py
ENV FLASK_DEBUG=0

ARG USER_ID=1000
ARG GROUP_ID=1000

ARG USER_ID=1000
ARG GROUP_ID=1000

# User mit Host-UID/GID erstellen
RUN groupadd -g ${GROUP_ID} appgroup && \
    useradd -u ${USER_ID} -g appgroup -m appuser

# Arbeitsverzeichnisse erstellen und Berechtigungen setzen
RUN mkdir -p /app/output && \
    chown -R ${USER_ID}:${GROUP_ID} /app

USER appuser

CMD ["gunicorn", "--worker-class", "gevent", "--bind", "0.0.0.0:5001", "py_main_flask:app"]