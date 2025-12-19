
# Changelog — Stream Metadata Monitor

---

## [1.4.5] — 2025-01-19
### Improved
- Skrócono timeout ffprobe z 8s → 5s, aby uniknąć blokowania pętli async.
- Dodano logi diagnostyczne, gdy ffprobe zwraca pusty wynik lub brak metadanych.
- Ulepszono fallback dla MP3: jeśli `StreamTitle` jest pusty, wykonywana jest dodatkowa próba odczytu `ARTIST/TITLE`.
- Dodano sanity‑check dla tytułów (`"-"`, `" - "`, puste stringi).
- Poprawiono czytelność logów ostrzegawczych (kolor YELLOW).
- Zachowano pełną kompatybilność z 1.4.x (ffprobe‑only, bez parsera ICY).

### Fixed
- Naprawiono przypadki, w których ffprobe zwracało dane, ale były one odrzucane jako puste.
- Poprawiono obsługę błędów JSON przy odczycie tagów OGG/MP3.

---
## 1.4.4 — 2025-12-19
### Nowe funkcje
- Dodano obsługę MQTT user/pass
- Poprawiono stabilność połączenia MQTT
- Dodano logi błędów MQTT
- Poprawiono obsługę polskich znaków

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
