import json
import datetime
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

def parse_and_display():
    # Load the captured output (simulated here by fetching again or mocking if file existed)
    # Since I cannot 'read' the previous terminal output directly via file, I will re-fetch inside python 
    # OR better: I will write a script that does the fetch AND print.
    
    import urllib.request
    import ssl
    
    API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
    LOCATION = "KATL:9:US"
    url = f"https://api.weather.com/v1/location/{LOCATION}/forecast/daily/15day.json?units=e&language=en-US&apiKey={API_KEY}"
    
    print(f"Fetching 15-Day Forecast for {LOCATION}...")
    
    context = ssl._create_unverified_context()
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, context=context) as response:
            data = json.loads(response.read().decode('utf-8'))
            forecasts = data.get('forecasts', [])
            
            print(f"{'Date':<15} | {'MaxTemp (F)':<12} | {'Narrative'}")
            print("-" * 60)
            
            for f in forecasts:
                # fcst_valid_local gives the ISO string
                dt_str = f.get('fcst_valid_local', '')
                # Parse to YYYY-MM-DD
                # ex: 2026-01-07T07:00:00-0500
                date_part = dt_str.split('T')[0]
                
                max_t = f.get('max_temp')
                if max_t is None: max_t = "N/A"
                narrative = f.get('narrative', '')[:30] + "..."
                
                print(f"{date_part:<15} | {str(max_t):<12} | {narrative}")
                
    except Exception as e:
        print(f"Failed to fetch/parse: {e}")

if __name__ == "__main__":
    parse_and_display()
