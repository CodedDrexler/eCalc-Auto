from playwright.sync_api import sync_playwright
import time

def inspect_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Login
        print("--- Navigating to Login ---")
        page.goto("https://www.ecalc.ch/calcinclude/login.php") # Direct login link assumption or find it
        # Actually usually it is a popup or a specific page. Let's check main page.
        page.goto("https://www.ecalc.ch/")
        
        # Try to find login button
        try:
            # Often there is a 'member access' or 'login' button.
            # Let's dump buttons to see what we have if we fail
            pass
        except:
            pass
            
        # For the script, I'll assume standard POST or form. 
        # But let's look for known login inputs first.
        
        # Let's try direct to setupfinder, maybe it redirects to login?
        print("--- Navigating to SetupFinder to trigger Login or inspect ---")
        page.goto("https://www.ecalc.ch/setupfinder.php")
        time.sleep(2)
        
        # Check if we are on login page
        if "login" in page.url or page.locator("input[type='password']").count() > 0:
            print("Detected Login Page/Form")
            # Dump inputs
            inputs = page.locator("input").all()
            for i in inputs:
                name = i.get_attribute("name")
                id_ = i.get_attribute("id")
                placeholder = i.get_attribute("placeholder")
                type_ = i.get_attribute("type")
                print(f"Login Input: name={name}, id={id_}, type={type_}, placeholder={placeholder}")
                
            # Attempt Login
            print("Attempting Login...")
            # Common names: 'email', 'username', 'password'
            # Based on user description: "email: juliramosmello@gmail.com"
            
            # Fill logic (heuristic)
            page.fill("input[type='email']", "juliramosmello@gmail.com")
            page.fill("input[type='password']", "MTOW@2026")
            
            # Click submit
            # Look for button that says "Login" or "Entrar" or type="submit"
            page.click("button[type='submit'], input[type='submit']")
            page.wait_for_load_state("networkidle")
            print("Login submitted.")
        
        # 2. Setup Finder
        print("\n--- Inspecting Setup Finder (https://www.ecalc.ch/setupfinder.php) ---")
        page.goto("https://www.ecalc.ch/setupfinder.php")
        page.wait_for_load_state("domcontentloaded")
        
        inputs = page.locator("input, select").all()
        print(f"Found {len(inputs)} inputs/selects on Setup Finder")
        for i in inputs:
            tag = i.evaluate("el => el.tagName.toLowerCase()")
            name = i.get_attribute("name")
            id_ = i.get_attribute("id")
            if name or id_:
                print(f"SetupFinder: tag={tag}, name={name}, id={id_}")

        # 3. Prop Calc
        print("\n--- Inspecting Prop Calc (https://www.ecalc.ch/motorcalc.php) ---")
        page.goto("https://www.ecalc.ch/motorcalc.php")
        page.wait_for_load_state("domcontentloaded")
        
        inputs = page.locator("input, select").all()
        print(f"Found {len(inputs)} inputs/selects on Prop Calc")
        for i in inputs:
            tag = i.evaluate("el => el.tagName.toLowerCase()")
            name = i.get_attribute("name")
            id_ = i.get_attribute("id")
            if name or id_:
                print(f"PropCalc: tag={tag}, name={name}, id={id_}")

        browser.close()

if __name__ == "__main__":
    inspect_page()
