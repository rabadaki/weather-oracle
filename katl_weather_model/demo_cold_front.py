def demo_cold_front():
    print("--- Scenario: Jan 10 (69F) -> Jan 11 (Cold Front) ---")
    
    # 1. The Setup
    jan_10_temp = 69.0
    jan_11_forecast = 50.0 # From TWC API
    
    print(f"Yesterday (Jan 10): {jan_10_temp} F")
    print(f"TWC Forecast (Jan 11): {jan_11_forecast} F (Cold Front incoming)")
    print("-" * 40)
    
    # 2. Old Model (Statistical / Persistence)
    # It only knows "Yesterday was 69". It guesses "Tomorrow will be similar".
    old_pred = jan_10_temp * 0.98 # Mild decay
    print(f"Old Model (Blind): {old_pred:.1f} F")
    print(f"-> Logic: 'It was warm yesterday, it will be warm today.'")
    print(f"-> Result: MISS (Error ~18 F)")
    
    print("-" * 40)
    
    # 3. New Model (Hybrid / Physics-Informed)
    # It sees the TWC Forecast of 50.0.
    # It applies the Bias Correction (e.g., 'TWC usually underestimates cold by 1 degree').
    bias = 1.0 # Hypothetical learned bias
    new_pred = jan_11_forecast + bias
    
    print(f"New Model (Sighted): {new_pred:.1f} F")
    print(f"-> Logic: 'The Supercomputer says 50F. I trust it (+ small correction).'")
    print(f"-> Result: HIT (Error ~1 F)")

if __name__ == "__main__":
    demo_cold_front()
