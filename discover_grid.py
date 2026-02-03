from automation import ECalAutomator
import time

def discover_grid():
    auto = ECalAutomator(headless=False)
    try:
        auto.start()
        auto.login("juliramosmello@gmail.com", "MTOW@2026")
        auto.page.goto("https://www.ecalc.ch/setupfinder.php")
        
        # Dismiss overlays
        try:
             if auto.page.locator(".cookieinfo-close").count() > 0:
                 auto.page.click(".cookieinfo-close")
        except: pass
        
        auto.page.fill("#inAcAuw", "15000")
        auto.page.click("#btnFindSetup")
        time.sleep(10)
        
        # Discover grid
        grid_info = auto.page.evaluate("""() => {
            if (typeof w2ui === 'undefined') return "w2ui not defined";
            const grids = Object.keys(w2ui);
            const details = {};
            grids.forEach(g => {
                details[g] = {
                    records: w2ui[g].records ? w2ui[g].records.length : 0,
                    total: w2ui[g].total,
                    limit: w2ui[g].limit
                };
            });
            return details;
        }""")
        
        print("\nGRID DISCOVERY:")
        print(grid_info)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # auto.stop()
        pass

if __name__ == "__main__":
    discover_grid()
