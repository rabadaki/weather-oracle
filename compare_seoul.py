import json
import pandas as pd
import numpy as np

def compare_sources():
    # Load TWC (Fahrenheit)
    with open('twc_rksi_test.json') as f:
        twc_data = json.load(f)
        
    twc_temps = []
    for o in twc_data.get('observations', []):
        if o.get('temp') is not None:
            twc_temps.append(o['temp'])
            
    if not twc_temps:
        print("TWC Data Empty")
        return
        
    twc_max = max(twc_temps)
    twc_min = min(twc_temps)
    
    # Load OpenMeteo (Celsius -> Fahrenheit)
    with open('om_rksi_test.json') as f:
        om_data = json.load(f)
        
    om_temps_c = om_data.get('hourly', {}).get('temperature_2m', [])
    if not om_temps_c:
        print("OM Data Empty")
        return
        
    om_temps_f = [(c * 9/5) + 32 for c in om_temps_c if c is not None]
    om_max = max(om_temps_f)
    om_min = min(om_temps_f)
    
    print(f"--- Seoul (RKSI) 2024-01-01 Comparison ---")
    print(f"TWC (Observation): High {twc_max} F, Low {twc_min} F")
    print(f"OM (GFS Seamless): High {om_max:.2f} F, Low {om_min:.2f} F")
    
    diff = abs(twc_max - om_max)
    print(f"Difference: {diff:.2f} F")
    
    if diff < 1.0:
        print("CONCLUSION: Identical/Analysis Data. (BAD for Bias Training)")
    else:
        print("CONCLUSION: Distinct Data. Likely Forecast. (GOOD for Bias Training)")

if __name__ == "__main__":
    compare_sources()
