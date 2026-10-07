
import os
import json
import urllib.request
import urllib.parse

api_key = os.environ.get("BRSAPI_KEY")

if not api_key:
    raise ValueError("BRSAPI_KEY is missing!")

params = urllib.parse.urlencode({
    "key": api_key,
    "type": 1
})

url = "https://Api.BrsApi.ir/Tsetmc/Index.php?" + params

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

try:
    request = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)

    print("API response received successfully!")
    print(json.dumps(data, ensure_ascii=False, indent=2))

except Exception as e:
    print("API request failed:", type(e).__name__)
    raise
