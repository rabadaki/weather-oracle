import logging
from bot.jobs.market_scanner import MarketScanner
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from katl_weather_model.predict_seoul import predict_seoul
except ImportError as e:
    logger.error(f"Failed to import predict_seoul: {e}")
    raise e

def run_seoul_cycle():
    logger.info("Step 1: Running Seoul (RKSI) Weather Model...")
    try:
        model_result = predict_seoul()
        # Returns: {'prediction_c': 6.2, 'prediction_f': 43.1, 'date': '...'}
    except Exception as e:
        logger.error(f"Seoul Model Failed: {e}")
        return "❌ Seoul Model Error"

    pred_c = model_result['prediction_c']
    pred_f = model_result['prediction_f']
    target_date = model_result['date']
    
    logger.info(f"Model predicts {pred_c:.1f} C ({pred_f:.1f} F) for {target_date}")

    logger.info("Step 2: Scanning Seoul Market...")
    scanner = MarketScanner()
    dt_target = datetime.strptime(target_date, "%Y-%m-%d").date()
    
    markets = scanner.find_seoul_market(dt_target)
    
    if not markets:
        return f"🇰🇷 Seoul Forecast: **{pred_c:.1f}°C** / **{pred_f:.1f}°F**\nStats: Markets closed/not found."

    # Step 3: Compare
    logger.info("Step 3: Compare")
    report = [f"🇰🇷 **The Seoul Oracle** ({target_date})"]
    
    # Detailed Breakdown
    comps = model_result.get('components', {})
    jma_val = comps.get('JMA_Raw_C')
    ml_val = comps.get('Pure_ML_C')
    
    breakdown_str = f"(JMA GSM: {jma_val:.1f}°C | ML: {ml_val:.1f}°C)"
    
    report.append(f"My Prediction: **{pred_c:.1f}°C** ({pred_f:.1f}°F)")
    report.append(f"_{breakdown_str}_")
    
    for m in markets:
        strike = m['strike']
        question = m['question']
        
        # UNIT DETECTION
        # If strike > 20, it's likely Fahrenheit (Seoul winter is rarely > 20C)
        # If strike < 15, it's likely Celsius.
        # This is a heuristic.
        
        is_fahrenheit = strike > 20
        unit = "F" if is_fahrenheit else "C"
        
        # LOGIC UPGRADE:
        # Detect: "or below" (Lower), "or higher" (Higher), or "Exact" (Bin)
        
        q_lower = question.lower()
        if "or below" in q_lower or "less" in q_lower:
            m_type = "LOWER"  # Want Pred < Strike
            # Edge: Strike - Pred. (e.g. Strike 2, Pred 9 -> 2-9 = -7. BAD)
            # e.g. Strike 10, Pred 9 -> 10-9 = +1. GOOD.
            if is_fahrenheit: 
                edge = strike - pred_f
            else:
                edge = strike - pred_c
                
        elif "or higher" in q_lower or "more" in q_lower or "above" in q_lower:
            m_type = "HIGHER" # Want Pred > Strike
            if is_fahrenheit:
                edge = pred_f - strike
            else:
                edge = pred_c - strike
                
        else:
            m_type = "EXACT" # Want Pred ~= Strike
            # Standard bin width is usually 1 degree.
            # If Pred is 9.0, and Strike is 3. We want to be FAR AWAY.
            # If we just do Edge = Pred - Strike, 9-3=6. That implies YES. Wrong.
            # We want to SHORT if we are far away.
            # Distance metric.
            if is_fahrenheit:
                dist = abs(pred_f - strike)
            else:
                dist = abs(pred_c - strike)
            
            # Logic: If dist < 0.5, we like it. Edge = +Positive.
            # If dist > 2.0, we hate it. Edge = -Negative.
            # Let's define Edge as "Safety Margin". 
            # This is tricky for a simple "Edge" number.
            # Let's say Edge = 1.0 - dist.
            # If dist is 0 (Perfect), Edge = +1.0.
            # If dist is 6 (Way off), Edge = -5.0. 
            edge = 1.0 - dist

        # Thresholds
        if is_fahrenheit:
            valid_threshold = 1.9 
        else:
            valid_threshold = 0.9 # Lower slightly to catch "1.0" edge cases
            
        signal = "WAIT"
        icon = "😐"
        
        # Exact markets need a specialized threshold (harder to hit)
        if m_type == "EXACT":
            if edge > 0.2: # very close match
                signal = "BET YES"
                icon = "🟢"
            elif edge < -1.5: # definitely not it
                signal = "BET NO"
                icon = "🔴"
        else:
            # Directional Markets
            if edge >= valid_threshold: 
                signal = "BET YES"
                icon = "🟢"
            elif edge <= -valid_threshold: 
                signal = "BET NO" 
                icon = "🔴"
            else:
                 # In between -0.9 and +0.9
                 signal = f"WAIT (Edge {edge:+.1f} < {valid_threshold})"
                 icon = "😐"
            
        price_yes = scanner.get_price(m['token_yes'])
        
        report.append(f"\nQuestion: {question}")
        report.append(f"Type: {m_type} | Strike: **{strike}** | Edge: {edge:+.1f}{unit}")
        report.append(f"Signal: {icon} **{signal}**")
        if price_yes:
            report.append(f"Price (Yes): {price_yes:.2f}c")
            
    return "\n".join(report)

if __name__ == "__main__":
    print(run_seoul_cycle())
