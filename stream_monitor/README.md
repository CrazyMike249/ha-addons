# Stream Metadata Monitor — v1.4.0

Lekki, szybki i niezależny add-on do Home Assistant, który pobiera metadane
ze streamów radiowych (AAC/OGG/MP3) i wysyła je do logów oraz opcjonalnie do MQTT.

## Funkcje

- Obsługa AAC (ICY), MP3 (ICY), OGG/Vorbis (ARTIST/TITLE)
- Automatyczne wykrywanie typu streamu
- Async pooling — wszystkie stacje równolegle
- Kolorowe logi
- MQTT publish (retain=true)
- Zero zależności od Home Assistant API
- Zero WebSocketów, zero REST, zero tokenów
- Stabilny i lekki

## Konfiguracja

W `config.yaml`:

```yaml
interval: 5
timestamps: true

streams:
  - name: Radio357
    url: "https://stream.rcs.revma.com/ye5kghkgcm0uv.aac"
    type: aac

mqtt_enabled: true
mqtt_host: "homeassistant.local"
mqtt_port: 1883
mqtt_topic: "radio/metadata"
