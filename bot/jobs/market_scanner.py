import requests
import re
from datetime import datetime, timedelta

GAMMA_URL = "https://gamma-api.polymarket.com/events"
CLOB_URL = "https://clob.polymarket.com/price"

class MarketScanner:
    def __init__(self):
        self.session = requests.Session()

    def find_market(self, city_name="Atlanta", target_date=None):
        """
        Finds the 'High Temperature in {city_name}' market for a given date.
        """
        if target_date is None:
            target_date = datetime.now().date() + timedelta(days=1)
            
        date_formats = [
            target_date.strftime("%B %-d"), # "January 8"
            target_date.strftime("%b %-d"), # "Jan 8"
            target_date.strftime("%B %d"),  # "January 08"
        ]
        
        query_params = {
            "tag_slug": "weather",
            "closed": "false",
            "limit": 100
        }
        
        try:
            resp = self.session.get(GAMMA_URL, params=query_params)
            resp.raise_for_status()
            events = resp.json()
            
            # Robust Matching Strategy:
            # 1. Series Slug (Best): e.g. "atlanta-daily-weather"
            # 2. Title (Fallback): e.g. "Atlanta"
            
            target_slug = f"{city_name.lower()}-daily-weather"
            
            for event in events:
                title = event.get('title', '')
                series_slug = event.get('seriesSlug', '')
                
                # Check for Match
                is_match = False
                if target_slug == series_slug:
                    is_match = True
                elif city_name in title: # Fallback
                    is_match = True
                
                if is_match:
                     for d_str in date_formats:
                         if d_str in title:
                            return self._parse_markets(event['markets'])
        except Exception as e:
            print(f"Scanner Error: {e}")
            return []
        return []

    def find_atlanta_market(self, target_date=None):
        return self.find_market("Atlanta", target_date)

    def find_seoul_market(self, target_date=None):
        return self.find_market("Seoul", target_date)

    def _parse_markets(self, markets):
        results = []
        for m in markets:
            # Question: "Will the high temperature be >= 50F?"
            # Regex to find number
            q = m.get('question', '')
            # Match "50" from ">= 50F" or "Above 50F"
            match = re.search(r'(\d+)', q)
            if match:
                strike = int(match.group(1))
                # Get Token IDs
                # Usually outcomes are ["Yes", "No"]
                # JSON structure varies. Assuming standard.
                t_yes = m.get('clobTokenIds', [])[0] if len(m.get('clobTokenIds', [])) > 0 else None
                t_no = m.get('clobTokenIds', [])[1] if len(m.get('clobTokenIds', [])) > 1 else None
                
                results.append({
                    "strike": strike,
                    "token_yes": t_yes,
                    "token_no": t_no,
                    "question": q
                })
        return results

    def get_price(self, token_id):
        if not token_id: return None
        try:
            # side=SELL gives us the price we can buy at (The Ask).
            # side=BUY gives us the price we can sell at (The Bid).
            # We want to Buy Yes. So we check side=SELL.
            resp = self.session.get(CLOB_URL, params={"token_id": token_id, "side": "SELL"})
            data = resp.json()
            return float(data.get('price', 0.0))
        except:
            return None

if __name__ == "__main__":
    # Test Run
    ms = MarketScanner()
    print("Scanning for Weather Markets...")
    # Mocking date? No, let's scan for real markets.
    # Note: Gamma might return nothing if no active markets.
    markets = ms.find_atlanta_market(datetime.now().date())
    print(f"Found {len(markets)} brackets.")
