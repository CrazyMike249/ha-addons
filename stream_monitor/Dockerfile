FROM python:3.12-slim

# Instalacja ffmpeg (zawiera ffprobe)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Instalacja klienta MQTT
RUN pip install --no-cache-dir paho-mqtt

WORKDIR /app

COPY stream_monitor.py /app/stream_monitor.py
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

CMD ["/app/run.sh"]
