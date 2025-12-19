import asyncio
import subprocess
import json
from datetime import datetime
import paho.mqtt.client as mqtt

FFPROBE = "ffprobe"

# ---------------------------------------------------------
# Load config
# ---------------------------------------------------------

def load_options():
    try:
        with open("/data/options.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}

options = load_options()

INTERVAL = options.get("interval", 5)
USE_TIMESTAMPS = options.get("timestamps", False)
PRINT_CHANGES_ONLY = True

streams = {}
for entry in options.get("streams", []):
    name = entry.get("name")
    url = entry.get("url")
    stype = entry.get("type")
    if name and url:
        streams[name] = {"url": url, "type": stype}

last_titles = {name: None for name in streams}

# ---------------------------------------------------------
# Colors
# ---------------------------------------------------------

class Color:
    RESET = "\033[0m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"

def log(msg, color=Color.RESET):
    if USE_TIMESTAMPS:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{color}[{now}] {msg}{Color.RESET}", flush=True)
    else:
        print(f"{color}{msg}{Color.RESET}", flush=True)

# ---------------------------------------------------------
# ffprobe helper
# ---------------------------------------------------------

def run_ffprobe(cmd) -> bytes:
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8,
        )
        return result.stdout or b""
    except Exception:
        return b""

# ---------------------------------------------------------
# Decode text (PL-safe)
# ---------------------------------------------------------

def decode_text(data) -> str:
    if data is None:
        return ""

    if isinstance(data, str):
        raw = data.encode("latin1", errors="replace")
    else:
        raw = data

    for enc in ("utf-8", "iso-8859-2", "windows-1250", "latin1"):
        try:
            return raw.decode(enc)
        except UnicodeError:
            continue

    return raw.decode("utf-8", errors="replace")

# ---------------------------------------------------------
# ICY MP3 PARSER (wbudowany)
# ---------------------------------------------------------

async def icy_get_title(url: str) -> str | None:
    if not url.startswith("http://"):
        return None

    try:
        _, rest = url.split("://", 1)
        host_port, path = rest.split("/", 1)
        path = "/" + path

        if ":" in host_port:
            host, port = host_port.split(":", 1)
            port = int(port)
        else:
            host = host_port
            port = 80
    except Exception:
        return None

    reader = None
    writer = None

    try:
        reader, writer = await asyncio.open_connection(host, port)

        req = (
            f"GET {path} HTTP/1.0\r\n"
            f"Host: {host}\r\n"
            f"Icy-MetaData: 1\r\n"
            f"User-Agent: StreamMetadataMonitor/1.5.0\r\n"
            f"Connection: close\r\n\r\n"
        )
        writer.write(req.encode("ascii", errors="ignore"))
        await writer.drain()

        headers = b""
        while b"\r\n\r\n" not in headers:
            chunk = await reader.read(1024)
            if not chunk:
                return None
            headers += chunk

        header_block, rest = headers.split(b"\r\n\r\n", 1)
        header_text = header_block.decode("latin1", errors="ignore")

        metaint = 0
        for line in header_text.split("\r\n"):
            if line.lower().startswith("icy-metaint:"):
                try:
                    metaint = int(line.split(":", 1)[1].strip())
                except:
                    metaint = 0

        if metaint <= 0:
            return None

        already = len(rest)
        to_skip = max(metaint - already, 0)

        while to_skip > 0:
            chunk = await reader.read(min(4096, to_skip))
            if not chunk:
                return None
            to_skip -= len(chunk)

        meta_len_byte = await reader.read(1)
        if not meta_len_byte:
            return None

        meta_len = meta_len_byte[0] * 16
        if meta_len == 0:
            return None

        metadata = await reader.read(meta_len)
        if not metadata:
            return None

        text = metadata.decode("latin1", errors="ignore")

        marker = "StreamTitle='"
        if marker in text:
            title = text.split(marker, 1)[1].split("';", 1)[0]
            return decode_text(title).strip() or None

        return None

    except Exception:
        return None

    finally:
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass

# ---------------------------------------------------------
# AAC / OGG (ffprobe)
# ---------------------------------------------------------

def get_aac_streamtitle(url: str) -> str | None:
    cmd = [
        FFPROBE, "-loglevel", "quiet", "-icy", "1",
        "-show_entries", "format_tags=StreamTitle",
        "-of", "default=nw=1:nk=1", url,
    ]
    out = run_ffprobe(cmd)
    if not out:
        return None
    title = decode_text(out).strip()
    if not title or title in ("-", " - "):
        return None
    return title

def get_ogg_artist_title(url: str) -> str | None:
    cmd = [
        FFPROBE, "-loglevel", "quiet",
        "-show_entries", "stream_tags=ARTIST,TITLE,artist,title",
        "-of", "json", url,
    ]
    out = run_ffprobe(cmd)
    if not out:
        return None
    try:
        data = json.loads(decode_text(out))
        tags = data.get("streams", [{}])[0].get("tags", {})

        artist = decode_text(tags.get("ARTIST") or tags.get("artist") or "").strip()
        title  = decode_text(tags.get("TITLE")  or tags.get("title")  or "").strip()

        if artist and title:
            return f"{artist} – {title}"
        return artist or title or None
    except Exception:
        return None

# ---------------------------------------------------------
# Auto-detect
# ---------------------------------------------------------

async def get_metadata_async(url: str, stype: str | None) -> str | None:
    if stype == "aac":
        return get_aac_streamtitle(url)
    if stype == "ogg":
        return get_ogg_artist_title(url)
    if stype == "mp3":
        return await icy_get_title(url)

    title = await icy_get_title(url)
    if title:
        return title

    title = get_aac_streamtitle(url)
    if title:
        return title

    return get_ogg_artist_title(url)

# ---------------------------------------------------------
# MQTT
# ---------------------------------------------------------

MQTT_ENABLED = options.get("mqtt_enabled", False)
MQTT_HOST = options.get("mqtt_host", "localhost")
MQTT_PORT = options.get("mqtt_port", 1883)
MQTT_TOPIC = options.get("mqtt_topic", "radio/metadata")

MQTT_USER = options.get("mqtt_user")
MQTT_PASS = options.get("mqtt_pass")

mqtt_client = None

def mqtt_init():
    global mqtt_client
    if not MQTT_ENABLED:
        return

    mqtt_client = mqtt.Client(callback_api_version=2)

    if MQTT_USER and MQTT_PASS:
        mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)

    try:
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
        mqtt_client.loop_start()
        log(f"MQTT connected to {MQTT_HOST}:{MQTT_PORT}", Color.MAGENTA)
    except Exception as e:
        log(f"MQTT connection failed: {e}", Color.RED)

def mqtt_publish(name, title):
    if MQTT_ENABLED and mqtt_client:
        topic = f"{MQTT_TOPIC}/{name}"
        try:
            mqtt_client.publish(topic, title, qos=0, retain=True)
            log(f"MQTT → {topic}: {title}", Color.MAGENTA)
        except Exception as e:
            log(f"MQTT publish failed: {e}", Color.RED)

# ---------------------------------------------------------
# Async polling
# ---------------------------------------------------------

async def poll_single(name, info):
    url = info["url"]
    stype = info["type"]

    title = await get_metadata_async(url, stype)
    if not title:
        return

    if PRINT_CHANGES_ONLY and title == last_titles[name]:
        return

    last_titles[name] = title
    log(f"{name}: {title}", Color.GREEN)
    mqtt_publish(name, title)

async def poll_loop():
    while True:
        tasks = [poll_single(name, info) for name, info in streams.items()]
        await asyncio.gather(*tasks)
        await asyncio.sleep(INTERVAL)

# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":
    log("Start stream monitor (AAC/OGG + ICY MP3) v1.5.0", Color.CYAN)
    mqtt_init()
    asyncio.run(poll_loop())
