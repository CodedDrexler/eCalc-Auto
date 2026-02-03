from automation import ECalAutomator
import time

def inspect_pagination():
    auto = ECalAutomator(headless=False)
    inputs = {
        "weight": "15000",
        "wingspan": "3000",
        "wing_area": "150",
        "speed": "20",
        "thrust": "4000",
        "battery_cells": "6",
        "wing_type": "0" 
    }
    try:
        auto.start()
        auto.login("juliramosmello@gmail.com", "MTOW@2026")
        auto.page.goto("https://www.ecalc.ch/setupfinder.php")
        
        # Fill minimal values to get many results
        auto.page.fill("#inAcAuw", "15000")
        auto.page.click("#btnFindSetup")
        time.sleep(10)
        
        # Look for pagination buttons
        print("\n--- PAGINATION INSPECTION ---")
        
        # Common pagination patterns: .next, [title*='Next'], img[src*='next']
        next_button = auto.page.locator(".next, [title*='Next'], img[src*='next'], button:has-text('Next')")
        print(f"Next button count: {next_button.count()}")
        
        # Find all elements with 'Next' in them
        all_next = auto.page.locator("*:has-text('Next')").all()
        for i, el in enumerate(all_next):
             try:
                 print(f"Potential Next {i}: {el.get_attribute('class')} | {el.get_attribute('id')}")
             except: pass

        # Also check for the "1-17 of 2,860" text to see what element holds it
        status_text = auto.page.locator("*:has-text('of 2')")
        print(f"Status text elements: {status_text.count()}")
        for i in range(status_text.count()):
            try:
                print(f"Status {i}: {status_text.nth(i).inner_text()}")
            except: pass

    except Exception as e:
        print(f"Error: {e}")
    finally:
        auto.stop()

if __name__ == "__main__":
    inspect_pagination()
