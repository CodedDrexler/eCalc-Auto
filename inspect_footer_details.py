from automation import ECalAutomator
import time

def inspect_footer_details():
    auto = ECalAutomator(headless=False)
    try:
        auto.start()
        auto.login("juliramosmello@gmail.com", "MTOW@2026")
        auto.page.goto("https://www.ecalc.ch/setupfinder.php")
        
        auto.page.fill("#inAcAuw", "15000")
        auto.page.click("#btnFindSetup")
        time.sleep(15)
        
        # Get all children of the footer with their tags and classes
        footer_details = auto.page.evaluate("""() => {
            const footer = document.getElementById('grid_grid_footer');
            if (!footer) return "Footer not found";
            const items = footer.querySelectorAll('*');
            const res = [];
            items.forEach(el => {
                res.push({
                    tag: el.tagName,
                    id: el.id,
                    class: el.className,
                    title: el.getAttribute('title'),
                    onclick: el.getAttribute('onclick'),
                    text: el.innerText
                });
            });
            return res;
        }""")
        
        print("\nFOOTER INTERNAL STRUCTURE:")
        for item in footer_details:
             if 'next' in str(item).lower() or 'page' in str(item).lower() or 'w2ui-icon' in str(item).lower():
                print(item)

    except Exception as e:
        print(f"Error: {e}")
    finally:
        auto.stop()

if __name__ == "__main__":
    inspect_footer_details()
