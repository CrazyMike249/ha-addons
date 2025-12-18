import asyncio
import subprocess
import json
import time
from datetime import datetime
import paho.mqtt.client as mqtt

FFPROBE = "ffprobe"

# ---------------------------------------------------------
# Konfiguracja
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
# Kolory logów
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

def run_ffprobe(cmd):
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            timeout=8,
        )
        return result.stdout.strip()
    except Exception:
        return None

# ---------------------------------------------------------
# Dekodowanie tekstu
# ---------------------------------------------------------

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

# ---------------------------------------------------------
# AAC / OGG / MP3 (ICY)
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
    title = out.strip()
    if not title or title in ("-", " - "):
        return None
    return decode_text(title)

def get_ogg_artist_title(url: str) -> str | None:
    cmd = [
        FFPROBE, "-loglevel", "quiet",
        "-show_entries", "stream_tags=ARTIST,TITLE",
        "-of", "json", url,
    ]
    out = run_ffprobe(cmd)
    if not out:
        return None
    try:
        data = json.loads(out)
        tags = data.get("streams", [{}])[0].get("tags", {})
        artist = decode_text(tags.get("ARTIST", "").strip())
        title = decode_text(tags.get("TITLE", "").strip())
        if artist and title:
            return f"{artist} – {title}"
        return artist or title or None
    except Exception:
        return None

def get_mp3_icy(url: str) -> str | None:
    cmd = [
        FFPROBE, "-loglevel", "quiet", "-icy", "1",
        "-show_entries", "format_tags=StreamTitle",
        "-of", "default=nw=1:nk=1", url,
    ]
    out = run_ffprobe(cmd)
    if not out:
        return None
    title = out.strip()
    if not title or title in ("-", " - "):
        return None
    return decode_text(title)

# ---------------------------------------------------------
# Auto-detect
# ---------------------------------------------------------

def get_metadata(url: str, stype: str | None) -> str | None:
    if stype == "aac":
        return get_aac_streamtitle(url)
    if stype == "ogg":
        return get_ogg_artist_title(url)
    if stype == "mp3":
        return get_mp3_icy(url)

    for fn in (get_aac_streamtitle, get_mp3_icy, get_ogg_artist_title):
        title = fn(url)
        if title:
            return title
    return None

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

    title = get_metadata(url, stype)
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
    log("Start stream monitor (async + MP3 + MQTT + colors) v1.4.1", Color.CYAN)
    mqtt_init()
    asyncio.run(poll_loop())
