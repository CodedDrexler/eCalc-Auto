from automation import ECalAutomator
import time

def full_footer_dump():
    auto = ECalAutomator(headless=False)
    try:
        auto.start()
        auto.login("juliramosmello@gmail.com", "MTOW@2026")
        auto.page.goto("https://www.ecalc.ch/setupfinder.php")
        
        auto.page.fill("#inAcAuw", "15000")
        auto.page.click("#btnFindSetup")
        time.sleep(15)
        
        # Get all children of the footer
        all_elements = auto.page.evaluate("""() => {
            const footer = document.getElementById('grid_grid_footer');
            if (!footer) return [];
            const items = footer.querySelectorAll('*');
            return Array.from(items).map(el => ({
                tag: el.tagName,
                id: el.id,
                class: el.className,
                text: el.innerText.trim(),
                title: el.getAttribute('title')
            }));
        }""")
        
        print(f"\nTOTAL ELEMENTS IN FOOTER: {len(all_elements)}")
        for i, el in enumerate(all_elements):
            if el['tag'] in ['TABLE', 'TR', 'TD', 'SPAN', 'DIV', 'BUTTON', 'A', 'IMG']:
                print(f"{i}: {el}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        auto.stop()

if __name__ == "__main__":
    full_footer_dump()
