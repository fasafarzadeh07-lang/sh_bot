
import urllib.request
import time

urls = {
    "BrsApi": "https://BrsApi.ir",
    "TSE Gateway": "https://webgw.tse.ir",
}

for name, url in urls.items():
    print(f"\nTesting {name}...", flush=True)
    start = time.monotonic()

    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        with urllib.request.urlopen(
            request, timeout=10
        ) as response:
            print("HTTP status:", response.status)

    except Exception as e:
        print("Result:", str(e))

    print(
        "Elapsed:",
        round(time.monotonic() - start, 1),
        "seconds"
    )
