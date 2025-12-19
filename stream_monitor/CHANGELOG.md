# Changelog — Stream Metadata Monitor

## [1.5.0] — 2025-12-19
### Added
- Własny parser ICY dla MP3 (niezależny od ffprobe)
- Pełna obsługa polskich znaków (UTF‑8, ISO‑8859‑2, Windows‑1250, Latin‑1)
- Stabilny async pooling (każdy stream w osobnym tasku)
- Lepsze logowanie (kolory, timestampy, tryb „tylko zmiany”)

### Improved
- Kolejność fallbacków metadanych
- Stabilność połączeń TCP (zamknięcia socketów)
- Obsługa błędów bez crashowania add‑onu

### Fixed
- MP3 nie działało na systemach bez ICY w ffprobe
- ffprobe potrafiło blokować cały addon
- Niektóre stacje zwracały krzaczki w tytułach