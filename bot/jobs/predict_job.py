import logging
# Add parent dir to path if needed, or rely on root execution
from bot.jobs.market_scanner import MarketScanner

logger = logging.getLogger(__name__)

try:
    from katl_weather_model.predict_live import predict_live
except ImportError as e:
    logger.error(f"Failed to import predict_live: {e}")
    raise e

def run_prediction_cycle():
    """
    1. Run Weather Model.
    2. Scan Polymarket.
    3. Generate Signal.
    """
    logger.info("Step 1: Running KATL Weather Model...")
    try:
        model_result = predict_live()
        # Returns: {'prediction': 54.2, 'date': '2024-01-08', 'source': 'MOS'}
    except Exception as e:
        logger.error(f"Model Failed: {e}")
        return "❌ Model Error"

    pred_val = model_result['prediction']
    target_date = model_result['date']
    
    logger.info(f"Model predicts {pred_val:.1f} F for {target_date}")

    logger.info("Step 2: Scanning Market...")
    scanner = MarketScanner()
    # Find market for target date (e.g. Tomorrow)
    # We need to parse target_date string back to datetime object slightly inefficient but safe
    from datetime import datetime
    dt_target = datetime.strptime(target_date, "%Y-%m-%d").date()
    
    markets = scanner.find_atlanta_market(dt_target)
    
    if not markets:
        return f"🌦 Forecast: **{pred_val:.1f}°F** ({model_result['source']})\nStats: Markets closed/not found."

    # Step 3: Compare
    report = [f"🔮 **The Oracle Report** ({target_date})"]
    
    # Detailed Breakdown
    comps = model_result.get('components', {})
    mos_val = comps.get('MOS')
    ml_val = comps.get('Pure_ML')
    bias_val = comps.get('Bias_Adj')
    
    breakdown_str = f"(MOS: {mos_val} | ML: {ml_val:.1f})"
    if bias_val:
        breakdown_str += f" [Bias: {bias_val:+.2f}]"
        
    report.append(f"My Prediction: **{pred_val:.1f}°F**")
    report.append(f"_{breakdown_str}_")
    
    for m in markets:
        strike = m['strike']
        question = m['question']
        
        # Logic: If Pred > Strike + 2.0 -> YES
        # If Pred < Strike - 2.0 -> NO
        # Else -> NEUTRAL
        
        edge = pred_val - strike
        signal = "WAIT"
        icon = "😐"
        
        if edge > 1.5: 
            signal = "BET YES"
            icon = "🟢"
        elif edge < -1.5: 
            signal = "BET NO" 
            icon = "🔴"
            
        # Get Price
        # Start with YES token
        price_yes = scanner.get_price(m['token_yes'])
        price_no = scanner.get_price(m['token_no'])
        
        # Display
        report.append(f"\nQuestion: {question}")
        report.append(f"Strike: **{strike}** | Edge: {edge:+.1f}F")
        report.append(f"Signal: {icon} **{signal}**")
        if price_yes:
            report.append(f"Price (Yes): {price_yes:.2f}c")
            
    return "\n".join(report)

if __name__ == "__main__":
    print(run_prediction_cycle())
