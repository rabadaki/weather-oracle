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
    report = [f"🇰🇷 **The Seoul Oracle** ({target_date})"]
    report.append(f"My Prediction: **{pred_c:.1f}°C** ({pred_f:.1f}°F)")
    
    for m in markets:
        strike = m['strike']
        question = m['question']
        
        # UNIT DETECTION
        # If strike > 20, it's likely Fahrenheit (Seoul winter is rarely > 20C)
        # If strike < 15, it's likely Celsius.
        # This is a heuristic.
        
        is_fahrenheit = strike > 20
        unit = "F" if is_fahrenheit else "C"
        
        if is_fahrenheit:
            edge = pred_f - strike
            threshold = 2.0 # F
        else:
            edge = pred_c - strike
            threshold = 1.0 # C
            
        signal = "WAIT"
        icon = "😐"
        
        if edge > threshold: 
            signal = "BET YES"
            icon = "🟢"
        elif edge < -threshold: 
            signal = "BET NO" 
            icon = "🔴"
            
        price_yes = scanner.get_price(m['token_yes'])
        
        report.append(f"\nQuestion: {question}")
        report.append(f"Strike: **{strike}** | Edge: {edge:+.1f}{unit}")
        report.append(f"Signal: {icon} **{signal}**")
        if price_yes:
            report.append(f"Price (Yes): {price_yes:.2f}c")
            
    return "\n".join(report)

if __name__ == "__main__":
    print(run_seoul_cycle())
