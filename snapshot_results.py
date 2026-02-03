from automation import ECalAutomator
import time

def snapshot_results():
    auto = ECalAutomator(headless=False)
    try:
        auto.start()
        auto.login("juliramosmello@gmail.com", "MTOW@2026")
        auto.page.goto("https://www.ecalc.ch/setupfinder.php")
        
        auto.page.fill("#inAcAuw", "15000")
        auto.page.click("#btnFindSetup")
        time.sleep(15)
        
        # Take screenshot
        auto.page.screenshot(path="setup_finder_results.png")
        print("Screenshot saved to setup_finder_results.png")
        
        # Get all button and link attributes near the bottom
        elements = auto.page.evaluate("""() => {
            const results = [];
            const all = document.querySelectorAll('button, a, img, div[class*="page"], div[class*="grid"]');
            all.forEach(el => {
                if (el.innerText.includes('of') || el.title.includes('Next') || el.className.includes('next') || el.src?.includes('next')) {
                    results.push({
                        tag: el.tagName,
                        id: el.id,
                        class: el.className,
                        text: el.innerText,
                        title: el.title,
                        src: el.src
                    });
                }
            });
            return results;
        }""")
        
        print("\nPotential Pagination Elements:")
        for el in elements:
            print(el)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        auto.stop()

if __name__ == "__main__":
    snapshot_results()
