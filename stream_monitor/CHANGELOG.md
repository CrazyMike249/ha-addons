
---

# 📘 **CHANGELOG.md (wersja 2.0.0)**

```markdown
# Changelog

## 2.0.0
### Duża aktualizacja architektury add-onu
- Usunięto listę stacji z konfiguracji (`streams:`).
- Add-on pobiera URL streamu **bezpośrednio z `media_content_id`** encji `media_player`.
- Dodano pełną integrację z Home Assistant przez **WebSocket API**.
- Dodano monitorowanie wybranych encji `media_player` (lista `players:`).
- Dodano logowanie startu/stopu odtwarzania:
  - `[HA] media_player.salon → PLAYING (URL)`
  - `[HA] media_player.salon → STOPPED`
- Dodano dynamiczne uruchamianie i zatrzymywanie pollingu metadanych.
- Dodano obsługę wielu playerów jednocześnie.
- Dodano automatyczny reconnect WebSocket.
- Uproszczono konfigurację — brak konieczności definiowania stacji.
- Kod został przeorganizowany i zoptymalizowany.

## 1.3.0
- Usunięto stacje zaszyte w kodzie.
- Dodano jedną listę `streams` w konfiguracji.
- Uproszczono logikę pobierania metadanych.
- Przygotowanie pod MQTT.

## 1.2.0
- Migracja konfiguracji do `config.yaml`.
- Dodano obsługę nazw stacji.
- Rozszerzono konfigurację o interval, timestamps, custom streams.

## 1.1.0
- Dodano konfigurację: interval, timestamps, custom streams, MQTT.
- Dodano możliwość wyłączania stacji.

## 1.0.0
- Pierwsza działająca wersja add-onu.
