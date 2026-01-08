
# Validates the betting logic for Atlanta Markets (Ranges & Directions)

def get_signal(pred_val, strike, question):
    q_lower = question.lower()
    
    # 1. Lower Bound ("61 or below")
    if "or below" in q_lower or "less" in q_lower:
         m_type = "LOWER"
         edge = strike - pred_val
         
    # 2. Higher Bound ("72 or higher")
    elif "or higher" in q_lower or "above" in q_lower:
         m_type = "HIGHER"
         edge = pred_val - strike
         
    # 3. Specific Range ("between 62 and 63")
    elif "between" in q_lower or "-" in q_lower:
         m_type = "BIN"
         dist = abs(pred_val - strike)
         edge = 1.0 - dist
         
    else:
         m_type = "HIGHER"
         edge = pred_val - strike
         
    signal = "WAIT"
    
    # Thresholds
    if m_type == "BIN":
        if edge > 0.5: # Dist < 0.5
             signal = "BET YES"
        elif edge < -2.0: # Dist > 3.0
             signal = "BET NO"
    else:
        # Directional
        if edge > 2.0: 
            signal = "BET YES"
        elif edge < -2.0: 
            signal = "BET NO"
            
    return m_type, edge, signal

# --- Test Cases (Based on User Report) ---
# Pred is 72.0
scenarios = [
    {"pred": 72.0, "strike": 61, "q": "61 or below", "expect": "BET NO"},
    {"pred": 72.0, "strike": 62, "q": "between 62-63", "expect": "BET NO"},
    {"pred": 72.0, "strike": 64, "q": "between 64-65", "expect": "BET NO"},
    {"pred": 72.0, "strike": 68, "q": "between 68-69", "expect": "BET NO"}, # Dist = 4. Edge = -3.
    {"pred": 72.0, "strike": 70, "q": "between 70-71", "expect": "WAIT"},   # Dist = 2. Edge = -1. (Wait zone)
    {"pred": 72.0, "strike": 72, "q": "72 or higher", "expect": "WAIT"},     # Edge 0.
    {"pred": 72.0, "strike": 69, "q": "69 or higher", "expect": "BET YES"},  # Edge +3.
]

print(f"{'Question':<20} | {'Pred':<5} | {'Strike':<6} | {'Type':<8} | {'Edge':<5} | {'Signal':<8} | {'Status'}")
print("-" * 85)

for s in scenarios:
    m_type, edge, signal = get_signal(s['pred'], s['strike'], s['q'])
    status = "✅ PASS" if signal == s['expect'] else f"❌ FAIL (Exp {s['expect']})"
    print(f"{s['q']:<20} | {s['pred']:<5} | {s['strike']:<6} | {m_type:<8} | {edge:<5.1f} | {signal:<8} | {status}")
