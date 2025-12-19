import asyncio


async def icy_get_title(url: str) -> str | None:
    """
    Pobiera StreamTitle z MP3/ICY bez ffprobe.
    Działa z RMF, BBC, MAXXX, Eska, ZET, Paradise, SomaFM itd.
    Zwraca tytuł lub None.
    """

    # Obsługujemy tylko http, bez https (większość streamów radiowych)
    if not url.startswith("http://"):
        return None

    # Rozbijamy URL na host, port i ścieżkę
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
        # Nawiązujemy połączenie TCP
        reader, writer = await asyncio.open_connection(host, port)

        # Wysyłamy żądanie HTTP z nagłówkiem Icy-MetaData: 1
        request = (
            f"GET {path} HTTP/1.0\r\n"
            f"Host: {host}\r\n"
            f"Icy-MetaData: 1\r\n"
            f"User-Agent: StreamMetadataMonitor/1.5.0\r\n"
            f"Connection: close\r\n\r\n"
        )
        writer.write(request.encode("ascii", errors="ignore"))
        await writer.drain()

        # Czytamy nagłówki HTTP/ICY
        headers = b""
        while b"\r\n\r\n" not in headers:
            chunk = await reader.read(1024)
            if not chunk:
                return None
            headers += chunk

        header_block, rest = headers.split(b"\r\n\r\n", 1)
        header_text = header_block.decode("latin1", errors="ignore")

        # Szukamy metaint
        metaint = 0
        for line in header_text.split("\r\n"):
            if line.lower().startswith("icy-metaint:"):
                try:
                    metaint = int(line.split(":", 1)[1].strip())
                except Exception:
                    metaint = 0

        if metaint <= 0:
            # Serwer nie wysyła ICY metadata
            return None

        # Część audio z nagłówków już została wczytana do "rest"
        # Musimy odliczyć, ile bajtów audio już mamy
        already = len(rest)
        to_skip = max(metaint - already, 0)

        # Jeśli brakuje audio do pierwszego bloku metadanych, doczytujemy
        while to_skip > 0:
            chunk = await reader.read(min(4096, to_skip))
            if not chunk:
                return None
            to_skip -= len(chunk)

        # Pierwszy bajt po audio to długość bloku metadanych (w jednostkach 16 bajtów)
        meta_len_byte = await reader.read(1)
        if not meta_len_byte:
            return None

        meta_len = meta_len_byte[0] * 16
        if meta_len == 0:
            # Brak metadanych w tym bloku
            return None

        metadata = await reader.read(meta_len)
        if not metadata:
            return None

        text = metadata.decode("latin1", errors="ignore")

        # Szukamy wzorca StreamTitle='...';
        marker = "StreamTitle='"
        if marker in text:
            title = text.split(marker, 1)[1].split("';", 1)[0]
            title = title.strip()
            return title or None

        return None

    except Exception:
        return None

    finally:
        if writer is not None:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
