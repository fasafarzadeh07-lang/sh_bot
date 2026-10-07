
import urllib.request
import urllib.error
import socket
import time

urls = {
    "General Internet": "https://www.google.com",
    "TSETMC Website": "https://www.tsetmc.com",
    "TSETMC CDN": "https://cdn.tsetmc.com",
    "TSETMC API": (
        "https://cdn.tsetmc.com/api/Index/"
        "GetIndexB1LastAll/All/1"
    ),
}

for name, url in urls.items():
    print(f"\nTesting: {name}", flush=True)
    print(f"URL: {url}", flush=True)

    start = time.monotonic()

    try:
        host = urllib.request.urlparse(url).hostname
        ip = socket.gethostbyname(host)
        print(f"DNS resolved: {ip}", flush=True)

        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(
            request, timeout=10
        ) as response:
            print(
                f"SUCCESS: HTTP {response.status}",
                flush=True
            )

    except Exception as e:
        print(
            f"FAILED: {type(e).__name__}: {e}",
            flush=True
        )

    elapsed = time.monotonic() - start
    print(f"Elapsed: {elapsed:.1f}s", flush=True)
