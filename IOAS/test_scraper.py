import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

print("Testing Unstop API...")
try:
    # Unstop API for hackathons
    resp = requests.get("https://unstop.com/api/public/opportunity/search-result?opportunity=hackathons", headers=headers)
    print("Unstop:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        items = data.get('data', {}).get('data', [])
        if items:
            item = items[0]
            print("First item keys:", item.keys())
            print("Sample Title:", item.get('title'))
            print("Sample URL:", item.get('seo_url'))
            print("Start:", item.get('start_date'))
            print("End:", item.get('end_date'))
        else:
            print("No items in data structure", data)
except Exception as e:
    print(e)
