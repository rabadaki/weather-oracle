
# Validates the betting logic for Seoul Markets
# Simulating the logic block from seoul_job.py

def get_signal(pred_c, strike, question):
    is_fahrenheit = False # Seoul usually Celsius
    q_lower = question.lower()
    
    # --- LOGIC START ---
    if "or below" in q_lower or "less" in q_lower:
        m_type = "LOWER"
        edge = strike - pred_c
            
    elif "or higher" in q_lower or "more" in q_lower or "above" in q_lower:
        m_type = "HIGHER"
        edge = pred_c - strike
            
    else:
        m_type = "EXACT" 
        dist = abs(pred_c - strike)
        edge = 1.0 - dist

    # Thresholds
    valid_threshold = 0.9 # C
    
    signal = "WAIT"
    
    # Exact markets need a specialized threshold
    if m_type == "EXACT":
        if edge > 0.2: 
            signal = "BET YES"
        elif edge < -1.5:
            signal = "BET NO"
    else:
        # Directional
        if edge >= valid_threshold: 
            signal = "BET YES"
        elif edge <= -valid_threshold: 
            signal = "BET NO"
            
    return m_type, edge, signal

# --- Test Cases ---
scenarios = [
    {"pred": 9.0, "strike": 2, "q": "2C or below", "expect": "BET NO"},
    {"pred": 9.0, "strike": 8, "q": "8C or higher", "expect": "BET YES"},
    {"pred": 6.0, "strike": 7, "q": "7C or higher", "expect": "BET NO"}, # User Case
    {"pred": 9.0, "strike": 3, "q": "3C", "expect": "BET NO"},           # Exact Mismatch
    {"pred": 9.0, "strike": 9, "q": "9C", "expect": "BET YES"},          # Exact Match
    {"pred": 9.2, "strike": 9, "q": "9C", "expect": "BET YES"},          # Exact (Close enough)
    {"pred": 5.0, "strike": 5, "q": "5C or higher", "expect": "WAIT"},   # Edge case (0 edge)
]

print(f"{'Question':<20} | {'Pred':<5} | {'Strike':<6} | {'Type':<8} | {'Edge':<5} | {'Signal':<8} | {'Status'}")
print("-" * 85)

for s in scenarios:
    m_type, edge, signal = get_signal(s['pred'], s['strike'], s['q'])
    status = "✅ PASS" if signal == s['expect'] else f"❌ FAIL (Exp {s['expect']})"
    print(f"{s['q']:<20} | {s['pred']:<5} | {s['strike']:<6} | {m_type:<8} | {edge:<5.1f} | {signal:<8} | {status}")
