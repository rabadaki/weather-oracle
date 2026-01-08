import requests
import json

def list_weather_markets():
    url = "https://gamma-api.polymarket.com/events"
    params = {
        "tag_slug": "weather",
        "closed": "false",
        "limit": 100 # Fetch more
    }
    
    print(f"Fetching {url}...")
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        events = resp.json()
        
        print(f"Found {len(events)} active weather events.")
        
        atlanta_count = 0
        for event in events:
            title = event.get('title', 'No Title')
            val = event.get('volume', '0')
            
            # Print ALL titles to see format
            # print(f"- {title} (Vol: {val})")
            
            if "Atlanta" in title or "Seoul" in title:
                print(f"✅ MATCH FOUND: {title}")
                print(json.dumps(event, indent=2))
                atlanta_count += 1
                
        if atlanta_count == 0:
            print("❌ No 'Atlanta' markets found in the top 100 weather events.")
            print("Sample of Top 5 Events:")
            for e in events[:5]:
                print(f"- {e.get('title')}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_weather_markets()
