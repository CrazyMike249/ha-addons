import subprocess
import time
import json
from datetime import datetime
import os

FFPROBE = "ffprobe"

# Wczytanie konfiguracji add-onu
def load_options():
    try:
        with open("/data/options.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}
        

options = load_options()

# Konfiguracja
INTERVAL = options.get("interval", 5)
USE_TIMESTAMPS = options.get("timestamps", False)

# Stacje wbudowane
streams = {}

if options.get("radio_357", True):
    streams["Radio 357"] = {
        "url": "https://stream.rcs.revma.com/ye5kghkgcm0uv",
        "type": "aac",
    }

if options.get("radio_nsw", True):
    streams["Radio Nowy Świat"] = {
        "url": "https://stream.nowyswiat.online/aac",
        "type": "aac",
    }

if options.get("radio_baobab", True):
    streams["Radio Baobab"] = {
        "url": "https://stream.radiobaobab.pl/radiobaobab.ogg",
        "type": "ogg",
    }

# Custom streams
for url in options.get("custom_streams", []):
    streams[url] = {"url": url, "type": "aac"}  # domyślnie AAC

last_titles = {name: None for name in streams}


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
        encoding="utf-8",
    )

    try:
        data = json.loads(result.stdout)
        streams_data = data.get("streams", [])
        if not streams_data:
            return None

        tags = streams_data[0].get("tags", {})
        artist = tags.get("ARTIST", "").strip()
        title = tags.get("TITLE", "").strip()

        if not artist and not title:
            return None

        if artist and title:
            return f"{artist} – {title}"
        return artist or title

    except Exception:
        return None


def poll_streams(interval: int) -> None:
    while True:
        for name, info in streams.items():
            url = info["url"]
            stype = info["type"]

            if stype == "aac":
                title = get_aac_streamtitle(url)
            elif stype == "ogg":
                title = get_ogg_artist_title(url)
            else:
                continue

            if title and title != last_titles[name]:
                last_titles[name] = title

                if USE_TIMESTAMPS:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{now}] {name}: {title}", flush=True)
                else:
                    print(f"{name}: {title}", flush=True)

        time.sleep(interval)


if __name__ == "__main__":
    poll_streams(INTERVAL)
