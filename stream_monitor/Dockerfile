ARG BUILD_FROM=ghcr.io/hassio-addons/base-python:13.2.0
FROM $BUILD_FROM

# ffmpeg/ffprobe
RUN apk add --no-cache ffmpeg

# MQTT client
RUN pip install --no-cache-dir paho-mqtt

COPY run.sh /
COPY stream_monitor.py /app/stream_monitor.py

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]

