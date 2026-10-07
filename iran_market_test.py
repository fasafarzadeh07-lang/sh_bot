
import json
import urllib.request

url = "https://cdn.tsetmc.com/api/Index/GetIndexB1LastAll/All/1"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

try:
    request = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)

    indexes = data.get("indexB1", [])

    print("Connection successful!")
    print("Number of index records:", len(indexes))

    if indexes:
        print("Sample record:")
        print(json.dumps(indexes[0], ensure_ascii=False, indent=2))
    else:
        print("No index records returned.")

except Exception as e:
    print("Connection failed!")
    print("Error:", str(e))
