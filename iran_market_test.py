
import pytse_client as tse

print("Testing pytse-client...", flush=True)

try:
    print("Downloading Foulad stock data...", flush=True)

    result = tse.download(
        symbols="فولاد",
        write_to_csv=False
    )

    history = result["فولاد"]

    if history.empty:
        raise ValueError("No stock data returned")

    print("SUCCESS! Data received.", flush=True)
    print("Latest records:", flush=True)
    print(history.tail(3).to_string(), flush=True)

except Exception as e:
    print("FAILED:", type(e).__name__, str(e), flush=True)
    raise
