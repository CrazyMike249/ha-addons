import subprocess
import time
import json
from datetime import datetime

FFPROBE = "ffprobe"


def load_options():
    try:
        with open("/data/options.json", "r") as f:
            return json.load(f)
    except Exception:
        return {}


options = load_options()

INTERVAL = options.get("interval", 5)
USE_TIMESTAMPS = options.get("timestamps", False)

# Wczytujemy wszystkie stacje z config.yaml
streams = {}

for entry in options.get("streams", []):
    name = entry.get("name")
    url = entry.get("url")
    stype = entry.get("type", "aac")

    if name and url:
        streams[name] = {"url": url, "type": stype}

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
            return f"{artist} â€“ {title}"
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
