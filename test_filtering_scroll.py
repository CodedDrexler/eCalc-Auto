from automation import ECalAutomator
import time

def test_filtering_and_scroll():
    print("Starting Scroll & Filter Verification Test...")
    auto = ECalAutomator(headless=False) 
    
    inputs = {
        "weight": "18000",
        "wingspan": "3900",
        "wing_area": "190.3",
        "speed": "20",
        "thrust": "5000",
        "battery_cells": "6",
        "wing_type": "0",
        "flight_plan": "3D - heavy"
    }
    
    # We want to scroll a bit to get enough data
    SCRAPE_LIMIT = 200 # Should trigger scrolling
    
    # Filter Checks
    TARGET_DIAM = 18.0
    TARGET_MANUF = "T-Motor" # Or T-Motor?
    
    try:
        auto.start()
        auto.login("juliramosmello@gmail.com", "MTOW@2026")
        
        print(f"\n--- STEP 1: SETUP FINDER (Requesting {SCRAPE_LIMIT} items) ---")
        setup_results = auto.run_setup_finder(inputs, limit=SCRAPE_LIMIT)
        
        print(f"Extracted {len(setup_results)} total setups.")
        
        if len(setup_results) < 50:
            print("WARNING: Extracted count is low. Scroll might not be working efficiently.")
        
        print(f"\n--- STEP 2: APPLYING FILTER (Diam={TARGET_DIAM}, Manuf={TARGET_MANUF}) ---")
        filtered = auto.filter_setups(setup_results, TARGET_DIAM, TARGET_MANUF)
        
        print(f"Filtered count: {len(filtered)}")
        for s in filtered[:10]: # Print first 10 matches
            print(f" - [{s['manufacturer']}] {s['motor_name']} | Prop: {s['prop_diam']}x{s['prop_pitch']}")
            
        print("\nTest Finished.")
             
    except Exception as e:
        print(f"\nERROR during test: {str(e)}")
    finally:
        print("\nClosing browser in 5 seconds...")
        time.sleep(5)
        auto.stop()

if __name__ == "__main__":
    test_filtering_and_scroll()
