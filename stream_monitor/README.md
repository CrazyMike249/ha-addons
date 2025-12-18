# Stream Metadata Monitor

Add-on dla Home Assistant, który monitoruje metadane streamów audio odtwarzanych przez wskazane encje `media_player.*`.  
Działa automatycznie: gdy player zaczyna odtwarzać stream, add-on pobiera metadane bezpośrednio z `media_content_id` i wypisuje je w logach.

Wspiera:
- ICY/AAC (`StreamTitle`)
- OGG/Vorbis (`ARTIST` + `TITLE`)
- dowolne źródła streamów (URL pobierany z HA, nic nie jest na sztywno)

---

## Funkcje

- Integracja z Home Assistant przez **WebSocket API**
- Monitorowanie wybranych encji `media_player`
- Automatyczne wykrywanie odtwarzania (`state == playing`)
- Pobieranie metadanych z URL znajdującego się w `media_content_id`
- Obsługa AAC/ICY oraz OGG/Vorbis
- Logowanie zmian tytułów w czasie rzeczywistym
- Obsługa wielu playerów jednocześnie
- Automatyczne zatrzymywanie pollingu, gdy player przestaje grać
- Odporność na rozłączenia WebSocket (auto-reconnect)

---

## Jak to działa

1. Add-on łączy się z Home Assistant przez WebSocket API.
2. Subskrybuje eventy `state_changed`.
3. Gdy wskazany `media_player`:
   - zmieni stan na `playing`
   - a w `media_content_id` znajduje się URL streamu

   → add-on uruchamia polling metadanych dla tego URL.

4. Gdy player przestaje grać → polling zostaje zatrzymany.

Przykładowe logi:

[HA] media_player.kuchnia → PLAYING (https://stream.nowyswiat.online/aac) media_player.kuchnia: Maanam – Kocham Cię, Kochanie Moje 
[HA] media_player.kuchnia → STOPPED

