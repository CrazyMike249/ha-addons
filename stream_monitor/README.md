# Stream Metadata Monitor

[![GitHub Release][releases-shield]][releases]

Add-on dla Home Assistant, któłry monitoruje metadane z internetowych stacji radiowych
(AAC/ICY oraz OGG/Vorbis) i wypisuje je w logach. Idealny jako baza pod integrację
z MQTT, automatyzacjami lub własnymi sensorami. Koniec z "Default media recevier" :).

---

## Funkcje

- Odczyt metadanych:
  - AAC/ICY (`StreamTitle`)
  - OGG/Vorbis (`ARTIST` + `TITLE`)
- Obsługa dowolnej liczby stacji
- Pełna konfiguracja w `config.yaml`
- Możliwość dodawania własnych stacji (name + url + type)
- Opcjonalne timestampy w logach
- Przygotowanie pod MQTT (opcjonalne)

---

## Konfiguracja

Wszystkie stacje znajdują się w jednej liście `streams`.

### Pola stacji:

| Pole | Opis |
|------|------|
| `name` | Nazwa stacji wyświetlana w logach |
| `url` | URL strumienia |
| `type` | `aac` lub `ogg` |

### Pola globalne:

| Pole | Opis |
|------|------|
| `interval` | Częstotliwość odpytywania (sekundy) |
| `timestamps` | Czy dodawać timestampy do logów |
| `mqtt_enabled` | Czy wysyłać dane do MQTT (na przyszłość) |
| `mqtt_host` | Adres brokera MQTT |
| `mqtt_port` | Port brokera |
| `mqtt_topic` | Topic dla metadanych |

---

## Przykładowe konfiguracje

### 1. Minimalna konfiguracja (tylko jedna stacja)

```yaml
interval: 5
timestamps: false

streams:
  - name: "Radio 357"
    url: "https://stream.rcs.revma.com/ye5kghkgcm0uv"
    type: "aac"

mqtt_enabled: false
mqtt_host: ""
mqtt_port: 1883
mqtt_topic: "radio/metadata"
