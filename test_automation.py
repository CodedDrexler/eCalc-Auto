from automation import ECalAutomator
import time

def test_extraction_limit():
    print("Starting Extraction Limit Verification Test...")
    auto = ECalAutomator(headless=False) 
    
    inputs = {
        "weight": "18000",
        "wingspan": "3900",
        "wing_area": "190.3",
        "speed": "20",
        "thrust": "5000",
        "battery_cells": "6",
        "wing_type": "0" 
    }
    
    # We want to verify it can extract more than 10
    REQUESTED_LIMIT = 50 
    
    try:
        auto.start()
        auto.login("juliramosmello@gmail.com", "MTOW@2026")
        
        print(f"\n--- STEP 1: SETUP FINDER (Requesting {REQUESTED_LIMIT}) ---")
        setup_results = auto.run_setup_finder(inputs, limit=REQUESTED_LIMIT)
        
        print(f"Extracted {len(setup_results)} setups.")
        
        if len(setup_results) > 10:
            print(f"\nSUCCESS: Extracting more than 10 setups works (Found {len(setup_results)})!")
        else:
            print(f"\nWARNING: Only found {len(setup_results)} setups. (Maybe eCalc list is short?)")
            
        if len(setup_results) > 0:
             print("First setup:", setup_results[0]['motor_name'])
             print("Last setup:", setup_results[-1]['motor_name'])
             
    except Exception as e:
        print(f"\nERROR during test: {str(e)}")
    finally:
        print("\nClosing browser in 5 seconds...")
        time.sleep(5)
        auto.stop()
        print("Test Finished.")

if __name__ == "__main__":
    test_extraction_limit()
