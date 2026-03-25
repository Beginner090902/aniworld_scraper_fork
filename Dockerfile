FROM python:3.14.3-slim

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

RUN groupadd -g 1000 appgroup \
    && useradd -u 1000 -g appgroup -m appuser


USER appuser

CMD ["python", "py_main_flask.py"]
