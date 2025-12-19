# 🎧 Stream Metadata Monitor  
### Home Assistant Add-on — AAC / OGG / MP3 Metadata Extractor (ffprobe-only)

![Addon Icon](./icon.png)

Stream Metadata Monitor to lekki i stabilny dodatek dla Home Assistant, który monitoruje metadane stacji radiowych (AAC, OGG, MP3) i publikuje je przez MQTT.  
Wersja **1.4.5** to dopracowana, stabilna odsłona linii 1.4.x — w pełni oparta na ffprobe, bez parsera ICY.

---

## 🚀 Funkcje

### 🎵 Obsługiwane formaty
| Format | Metoda | Status |
|--------|--------|--------|
| **MP3** | ffprobe (StreamTitle / ARTIST/TITLE) | ✔ |
| **AAC** | ffprobe | ✔ |
| **OGG** | ffprobe | ✔ |

### ⚙️ Funkcjonalność
- Stabilny async pooling (każdy stream w osobnym tasku)
- Publikacja metadanych przez MQTT
- Obsługa polskich znaków (UTF‑8, ISO‑8859‑2, Windows‑1250, Latin‑1)
- Kolorowe logi + opcjonalne timestampy
- Tryb „tylko zmiany”
- Minimalne opóźnienia dzięki skróconemu timeoutowi ffprobe

---

## 🖼️ Screenshoty

> *(Wstaw tu swoje screeny z HA — placeholdery poniżej)*

![Screenshot 1](./screenshots/ha_logs.png)
![Screenshot 2](./screenshots/ha_mqtt.png)

---

## 🛠 Konfiguracja (`options.json`)

```json
{
  "interval": 5,
  "timestamps": true,
  "mqtt_enabled": true,
  "mqtt_host": "core-mosquitto",
  "mqtt_port": 1883,
  "mqtt_topic": "radio/metadata",
  "streams": [
    {
      "name": "RMF",
      "url": "http://31.192.216.10:8000/rmf_fm",
      "type": "mp3"
    },
    {
      "name": "Radio357",
      "url": "https://stream.radio357.pl/stream.aac",
      "type": "aac"
    }
  ]
}
