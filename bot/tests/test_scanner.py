import unittest
from unittest.mock import MagicMock, patch
from bot.jobs.market_scanner import MarketScanner
from datetime import date

class TestScanner(unittest.TestCase):
    def setUp(self):
        self.scanner = MarketScanner()

    @patch('bot.jobs.market_scanner.requests.Session.get')
    def test_find_atlanta_market(self, mock_get):
        # Mock Gamma Response
        mock_event = {
            "title": "High Temperature in Atlanta on Jan 8?",
            "markets": [
                {
                    "question": "Will the high temp be >= 50F?",
                    "clobTokenIds": ["token_yes_123", "token_no_456"]
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = [mock_event]
        mock_get.return_value = mock_resp
        
        # Run
        # We need to simulate the date "Jan 8". 
        # But the scanner generates the date string internally based on input.
        # Let's override the date check logic or just pass a specific date.
        # Scanner code: target_date.strftime("%b %-d")
        
        # Let's fix the test date to match the mock title
        test_date = date(2024, 1, 8) 
        brackets = self.scanner.find_atlanta_market(test_date)
        
        self.assertEqual(len(brackets), 1)
        self.assertEqual(brackets[0]['strike'], 50)
        self.assertEqual(brackets[0]['token_yes'], "token_yes_123")

    @patch('bot.jobs.market_scanner.requests.Session.get')
    def test_get_price(self, mock_get):
        # Mock CLOB Response
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"price": "0.45"}
        mock_get.return_value = mock_resp
        
        price = self.scanner.get_price("token_123")
        self.assertEqual(price, 0.45)

if __name__ == "__main__":
    unittest.main()
