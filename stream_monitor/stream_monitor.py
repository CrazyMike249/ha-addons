import base64
import json
import os
import socket
import ssl
import subprocess
import threading
import time
from datetime import datetime
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

FFPROBE = "ffprobe"


# =========================================================
# Konfiguracja
# =========================================================

def load_options():
    try:
        with open("/data/options.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}


options = load_options()

INTERVAL = options.get("interval", 5)
USE_TIMESTAMPS = options.get("timestamps", False)

HA_URL = options.get("ha_url", "ws://supervisor/core/api/websocket")
HA_HTTP_URL = options.get("ha_http_url", "http://supervisor/core/api")
HA_TOKEN = options.get("ha_token", "")
PLAYERS = set(options.get("players", []))

# entity_id -> dict(url, thread, stop_event, last_title)
player_states = {}
lock = threading.Lock()


# =========================================================
# Logowanie
# =========================================================

def log(msg: str) -> None:
    if USE_TIMESTAMPS:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] {msg}", flush=True)
    else:
        print(msg, flush=True)


# =========================================================
# Pobieranie metadanych (AAC / OGG)
# =========================================================

def get_aac_streamtitle(url: str) -> str | None:
    cmd = [
        FFPROBE,
        "-loglevel", "quiet",
        "-icy", "1",
        "-show_entries", "format_tags=StreamTitle",
        "-of", "default=nw=1:nk=1",
        url,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )

    title = result.stdout.strip()
    return title or None


def decode_text(value: str) -> str:
    if not value:
        return value

    raw = value.encode("latin1", errors="ignore")

    for enc in ("utf-8", "iso-8859-2", "windows-1250", "latin1"):
        try:
            return raw.decode(enc)
        except Exception:
            pass

    return value


def get_ogg_artist_title(url: str) -> str | None:
    cmd = [
        FFPROBE,
        "-loglevel", "quiet",
        "-show_entries", "stream_tags=ARTIST,TITLE",
        "-of", "json",
        url,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="latin1",
    )

    try:
        data = json.loads(result.stdout)
        streams_data = data.get("streams", [])
        if not streams_data:
            return None

        tags = streams_data[0].get("tags", {})
        artist = decode_text(tags.get("ARTIST", "").strip())
        title = decode_text(tags.get("TITLE", "").strip())

        if not artist and not title:
            return None

        if artist and title:
            return f"{artist} – {title}"
        return artist or title

    except Exception as e:
        log(f"[META] Błąd parsowania OGG/Vorbis dla {url}: {e}")
        return None


def get_stream_metadata(url: str) -> str | None:
    """
    Najpierw próba ICY/AAC (StreamTitle), potem OGG/Vorbis (ARTIST + TITLE).
    Zwraca pojedynczy string z tytułem lub None.
    """
    title = get_aac_streamtitle(url)
    if title:
        return title

    title = get_ogg_artist_title(url)
    if title:
        return title

    return None


# =========================================================
# REST fallback: pobieranie media_content_id
# =========================================================

def get_media_url_via_rest(entity_id: str) -> str | None:
    if not HA_TOKEN:
        log(f"[REST] Brak ha_token – nie mogę pobrać URL dla {entity_id}")
        return None

    api_url = f"{HA_HTTP_URL.rstrip('/')}/states/{entity_id}"
    log(f"[REST] Pobieram media_content_id dla {entity_id} z {api_url}")

    req = Request(api_url)
    req.add_header("Authorization", f"Bearer {HA_TOKEN}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    try:
        with urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
    except HTTPError as e:
        log(f"[REST] HTTPError dla {entity_id}: {e.code} {e.reason}")
        return None
    except URLError as e:
        log(f"[REST] URLError dla {entity_id}: {e}")
        return None
    except Exception as e:
        log(f"[REST] Błąd podczas pobierania stanu {entity_id}: {e}")
        return None

    attributes = data.get("attributes", {})
    url = attributes.get("media_content_id")
    log(f"[REST] Odpowiedź REST dla {entity_id}: media_content_id={url!r}")

    if url and isinstance(url, str) and url.startswith("http"):
        log(f"[REST] media_content_id dla {entity_id}: {url}")
        return url

    log(f"[REST] Brak poprawnego media_content_id dla {entity_id}")
    return None


# =========================================================
# Polling metadanych dla konkretnego playera
# =========================================================

def polling_worker(entity_id: str, url: str, stop_event: threading.Event) -> None:
    log(f"[POLL] Start metadanych dla {entity_id} ({url})")

    last_title = None

    while not stop_event.is_set():
        try:
            title = get_stream_metadata(url)
            if title and title != last_title:
                last_title = title
                with lock:
                    state = player_states.get(entity_id)
                    if state is not None:
                        state["last_title"] = title

                log(f"[META] {entity_id} → zmiana metadanych: {title}")
        except Exception as e:
            log(f"[POLL] Błąd podczas pobierania metadanych dla {entity_id}: {e}")

        stop_event.wait(INTERVAL)

    log(f"[POLL] Stop metadanych dla {entity_id}")


def start_polling(entity_id: str, url: str) -> None:
    with lock:
        state = player_states.get(entity_id)

        if state is not None:
            log(f"[POLL] Restart pollingu dla {entity_id}")
            old_event = state.get("stop_event")
            old_thread = state.get("thread")
            if old_event is not None:
                old_event.set()
            if old_thread is not None and old_thread.is_alive():
                old_thread.join(timeout=1.0)

        log(f"[POLL] Uruchamiam polling dla {entity_id} (URL: {url})")

        stop_event = threading.Event()
        thread = threading.Thread(
            target=polling_worker, args=(entity_id, url, stop_event), daemon=True
        )

        player_states[entity_id] = {
            "url": url,
            "thread": thread,
            "stop_event": stop_event,
            "last_title": None,
        }

        thread.start()


def stop_polling(entity_id: str) -> None:
    with lock:
        state = player_states.get(entity_id)
        if not state:
            return

        log(f"[POLL] Zatrzymuję polling dla {entity_id}")

        stop_event = state.get("stop_event")
        thread = state.get("thread")

        if stop_event is not None:
            stop_event.set()
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)

        player_states.pop(entity_id, None)


# =========================================================
# Minimalny klient WebSocket
# =========================================================

class SimpleWebSocket:
    def __init__(self, url: str):
        self.url = url
        self.sock = None

    def connect(self):
        parsed = urlparse(self.url)

        scheme = parsed.scheme
        host = parsed.hostname
        port = parsed.port
        path = parsed.path or "/"

        if port is None:
            port = 443 if scheme == "wss" else 80

        log(f"[WS] Nawiązywanie połączenia TCP z {host}:{port} (scheme={scheme})")
        raw_sock = socket.create_connection((host, port), timeout=10)

        if scheme == "wss":
            context = ssl.create_default_context()
            self.sock = context.wrap_socket(raw_sock, server_hostname=host)
        else:
            self.sock = raw_sock

        # Po ustanowieniu połączenia – brak timeoutu na recv,
        # żeby brak eventów nie powodował rozłączenia.
        self.sock.settimeout(None)

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        headers = [
            f"GET {path} HTTP/1.1",
            f"Host: {host}:{port}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {key}",
            "Sec-WebSocket-Version: 13",
            "\r\n",
        ]
        request = "\r\n".join(headers)
        log(f"[WS] Wysyłam handshake WebSocket na {path}")
        self.sock.sendall(request.encode("ascii"))

        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.sock.recv(1024)
            if not chunk:
                raise ConnectionError("Brak odpowiedzi przy handshake WebSocket")
            response += chunk

        if b" 101 " not in response:
            raise ConnectionError(f"Handshake WebSocket nieudany: {response!r}")

        log("[WS] Handshake WebSocket OK")

    def send_text(self, message: str):
        if self.sock is None:
            raise ConnectionError("WebSocket niepołączony")

        payload = message.encode("utf-8")
        fin_opcode = 0x81  # FIN + text frame
        length = len(payload)

        header = bytearray()
        header.append(fin_opcode)

        mask_bit = 0x80
        if length <= 125:
            header.append(mask_bit | length)
        elif length < (1 << 16):
            header.append(mask_bit | 126)
            header += length.to_bytes(2, "big")
        else:
            header.append(mask_bit | 127)
            header += length.to_bytes(8, "big")

        mask_key = os.urandom(4)
        header += mask_key

        masked_payload = bytearray(
            b ^ mask_key[i % 4] for i, b in enumerate(payload)
        )

        log(f"[WS] Wysyłam frame tekstowy ({len(payload)} bajtów)")
        self.sock.sendall(header + masked_payload)

    def recv_text(self) -> str:
        if self.sock is None:
            raise ConnectionError("WebSocket niepołączony")

        first_two = self._recv_exact(2)
        if not first_two:
            raise ConnectionError("Połączenie zamknięte przy odbiorze")

        b1, b2 = first_two
        opcode = b1 & 0x0F
        masked = (b2 & 0x80) != 0
        length = b2 & 0x7F

        if length == 126:
            length_bytes = self._recv_exact(2)
            length = int.from_bytes(length_bytes, "big")
        elif length == 127:
            length_bytes = self._recv_exact(8)
            length = int.from_bytes(length_bytes, "big")

        mask_key = b""
        if masked:
            mask_key = self._recv_exact(4)

        payload = self._recv_exact(length)

        if masked:
            payload = bytes(
                b ^ mask_key[i % 4] for i, b in enumerate(payload)
            )

        # Frame zamykający
        if opcode == 0x8:
            raise ConnectionError("Otrzymano frame zamykający WebSocket")

        # Pong / ping / inne opcodes – ignorujemy, zostawiamy tylko text frames
        if opcode != 0x1:
            return ""

        return payload.decode("utf-8", errors="ignore")

    def _recv_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Połączenie zamknięte w trakcie odbioru")
            buf += chunk
        return buf

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        log("[WS] Połączenie WebSocket zamknięte")


# =========================================================
# Listener Home Assistant (WebSocket + REST fallback)
# =========================================================

def ha_listener():
    if not HA_TOKEN:
        log("[HA] Brak ha_token w konfiguracji – listener nie zostanie uruchomiony")
        return

    if not PLAYERS:
        log("[HA] Brak zdefiniowanych players w konfiguracji – listener nie zostanie uruchomiony")
        return

    log(f"[HA] Monitorowane encje: {', '.join(sorted(PLAYERS))}")

    while True:
        ws = SimpleWebSocket(HA_URL)
        try:
            log(f"[HA] Łączenie z {HA_URL}...")
            ws.connect()
            log("[HA] Połączono, wysyłam auth...")

            # Auth
            auth_msg = {
                "type": "auth",
                "access_token": HA_TOKEN,
            }
            ws.send_text(json.dumps(auth_msg))

            # Oczekujemy auth_required i auth_ok
            raw = ws.recv_text()
            if not raw:
                raise ConnectionError("Brak odpowiedzi auth_required z HA")

            msg = json.loads(raw)
            log(f"[HA] Odpowiedź auth_required/auth: {msg}")
            if msg.get("type") != "auth_required":
                log(f"[HA] Oczekiwano auth_required, otrzymano: {msg}")

            raw = ws.recv_text()
            if not raw:
                raise ConnectionError("Brak odpowiedzi auth_ok z HA")

            msg = json.loads(raw)
            log(f"[HA] Odpowiedź auth_ok: {msg}")
            if msg.get("type") != "auth_ok":
                raise ConnectionError(f"Auth nieudane: {msg}")

            log("[HA] Autoryzacja OK, subskrybuję state_changed...")

            sub_msg = {
                "id": 1,
                "type": "subscribe_events",
                "event_type": "state_changed",
            }
            ws.send_text(json.dumps(sub_msg))

            # Główna pętla odbierania
            while True:
                raw = ws.recv_text()
                if not raw:
                    continue

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    log("[HA] Otrzymano niepoprawny JSON – pomijam")
                    continue

                if data.get("type") != "event":
                    continue

                event = data.get("event", {})
                edata = event.get("data", {})
                entity_id = edata.get("entity_id")

                if entity_id not in PLAYERS:
                    continue

                new_state = edata.get("new_state") or {}
                state = new_state.get("state")
                attrs = new_state.get("attributes") or {}

                log(f"[HA] {entity_id} → stan: {state}, atrybuty: keys={list(attrs.keys())}")

                # Jeśli player gra – potrzebujemy URL
                if state == "playing":
                    stream_url = attrs.get("media_content_id")

                    if stream_url:
                        log(f"[HA] {entity_id} → URL z WebSocket: {stream_url}")
                    else:
                        log(f"[HA] {entity_id} → PLAYING bez media_content_id – próbuję REST")
                        stream_url = get_media_url_via_rest(entity_id)

                    if stream_url and isinstance(stream_url, str) and stream_url.startswith("http"):
                        log(f"[HA] {entity_id} → PLAYING ({stream_url})")
                        start_polling(entity_id, stream_url)
                    else:
                        log(f"[HA] {entity_id} → PLAYING, ale brak poprawnego URL – pomijam")
                else:
                    log(f"[HA] {entity_id} → STOPPED ({state})")
                    stop_polling(entity_id)

        except Exception as e:
            log(f"[WS] Błąd WebSocket: {e}. Ponowna próba za 5 sekund...")
            try:
                ws.close()
            except Exception:
                pass
            time.sleep(5)


# =========================================================
# Główna sekcja
# =========================================================

if __name__ == "__main__":
    log("[MAIN] Start stream_monitor – tryb uniwersalny (media_player + REST fallback, diagnostyka włączona).")
    log(f"[MAIN] Konfiguracja: interval={INTERVAL}, players={sorted(PLAYERS)}, ha_url={HA_URL}, ha_http_url={HA_HTTP_URL}")

    ha_thread = threading.Thread(target=ha_listener, daemon=True)
    ha_thread.start()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log("[MAIN] Zatrzymywanie...")
