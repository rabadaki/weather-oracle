import datetime
try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo

from fetch_twc_hourly import process_observations

def verify_fix():
    print("Verifying DST Fix for KATL (America/New_York)...")
    
    # Test Case: Nov 2, 2024 at 04:30 UTC.
    # This is BEFORE DST ends (DST ends Nov 3).
    # Correct (EDT, UTC-4): 00:30 on Nov 2. -> Bin: 2024-11-02
    # Incorrect (Old Logic would say EST, UTC-5): 23:30 on Nov 1. -> Bin: 2024-11-01
    
    dt_utc = datetime.datetime(2024, 11, 2, 4, 30, tzinfo=datetime.timezone.utc)
    ts = dt_utc.timestamp()
    
    mock_obs = [{
        'valid_time_gmt': ts,
        'temp': 70,
        'pressure': 30.0,
        'rh': 50,
        'wspd': 5,
        'precip_hrly': 0
    }]
    
    results = process_observations(mock_obs)
    
    print(f"Input UTC: {dt_utc}")
    print(f"Results keys: {list(results.keys())}")
    
    if "2024-11-02" in results:
        print("PASS: Correctly identified Nov 2 (EDT logic used).")
    elif "2024-11-01" in results:
        print("FAIL: Incorrectly identified Nov 1 (EST logic used).")
    else:
        print("FAIL: Unknown Date.")

if __name__ == "__main__":
    verify_fix()
