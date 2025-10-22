FROM python:3.9-slim
RUN apt-get update
RUN apt-get upgrade 
RUN apt-get install -y ffmpeg
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
#install ffmpeg

COPY . .
CMD ["python", "py_interaktive_multi_runner.py"]
