
---

# 🟦 **CHANGELOG.md (1.3.0 → 1.4.0)**

```markdown
# Changelog

## 1.4.0 — 2025-12-18
### Nowe funkcje
- Dodano obsługę MP3 (ICY metadata)
- Dodano async pooling (wszystkie stacje równolegle)
- Dodano kolorowe logi (zielony, magenta, cyan)
- Dodano integrację MQTT (opcjonalną)
- Dodano auto-detect typu streamu (AAC → MP3 → OGG)
- Dodano dekodowanie tekstu (UTF-8, ISO-8859-2, Windows-1250)

### Poprawki
- Stabilniejsze timeouty ffprobe
- Ignorowanie pustych tytułów typu "-" lub " - "
- Lepsza struktura kodu i modularność

## 1.3.0
- Oryginalna wersja bazowa (polling AAC/OGG)
