# Changelog

## 1.3.0
- Usunięto stacje zaszyte w kodzie.
- Dodano jedną listę `streams` w konfiguracji (name + url + type).
- Użytkownik może dowolnie usuwać, zmieniać i dodawać stacje.
- Kod uproszczony — jedna pętla obsługująca wszystkie źródła.
- Przygotowanie pod integrację MQTT i autodiscovery.

## 1.2.0
- Migracja konfiguracji z `config.json` do `config.yaml`.
- Dodano obsługę nazw dla `custom_streams`.
- Rozszerzono konfigurację o:
  - interval
  - timestamps
  - włączanie/wyłączanie stacji
  - custom streams (name + url + type)
  - ustawienia MQTT (na przyszłość)

## 1.1.0
- Dodano konfigurację: interval, timestamps, custom streams (bez nazw), MQTT.
- Dodano możliwość wyłączania stacji.

## 1.0.0
- Pierwsza działająca wersja add-onu.
