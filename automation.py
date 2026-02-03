from playwright.sync_api import sync_playwright
import time
from typing import List, Dict, Any
import os

class ECalAutomator:
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
        self.logged_in_alert_seen = False

    def start(self):
        self.playwright = sync_playwright().start()
        
        # Determine a profile directory to persist cookies/session
        profile_path = os.path.join(os.getcwd(), "ecalc_session")
        if not os.path.exists(profile_path):
            os.makedirs(profile_path)

        # Launching a persistent context instead of a fresh browser every time
        self.browser = self.playwright.chromium.launch_persistent_context(
            profile_path,
            headless=self.headless,
            viewport={'width': 1366, 'height': 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = self.browser.pages[0]
        
        # Add dialog handler for alerts (like "Already logged in")
        def handle_dialog(dialog):
            try:
                msg = dialog.message.lower()
                print(f"[Alert] {dialog.message}")
                
                # If it's the "Already logged in" alert
                if "logged in" in msg or "angemeldet" in msg:
                    self.logged_in_alert_seen = True
                    time.sleep(1) # Brief pause
                
                try:
                    dialog.accept()
                except:
                    try:
                        dialog.dismiss()
                    except:
                        pass
            except Exception as e:
                pass
            
        self.page.on("dialog", handle_dialog)

    def stop(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def login(self, email, password):
        self.email = email
        self.password = password
        self.logged_in_alert_seen = False # Reset
        
        # FIRST: Check if we are already logged in via persistent cookies
        print(f"Checking if session is already active...")
        try:
            self.page.goto("https://www.ecalc.ch/motorcalc.php", timeout=30000)
            time.sleep(2)
            if self.page.locator("a:has-text('Logout')").count() > 0:
                print("Session resumed from cookies.")
                return True
        except: pass
        
        # If we saw the alert during the check above, we are logged in.
        if self.logged_in_alert_seen:
             print("Login alert detected during check. Session is active.")
             return True

        print(f"Navigating to login page...")
        try:
            self.page.goto("https://www.ecalc.ch/calcmember/login.php", timeout=60000)
            time.sleep(2)
        except Exception as e:
            print(f"Error navigating to login page: {e}")
            return False
            
        # If already logged in (redirected)
        if self.page.locator("a:has-text('Logout')").count() > 0 or "login.php" not in self.page.url:
             if "login.php" not in self.page.url:
                 print("Already logged in (Redirected).")
                 return True
            
        print(f"Logging in as {email}...")
        try:
            # Dismiss cookies if they block
            if self.page.locator(".cookieinfo-close").count() > 0:
                 self.page.click(".cookieinfo-close")
                 time.sleep(1)

            self.page.fill("input[name='username']", email)
            self.page.fill("input[name='password']", password)
            
            # Remember Me
            try:
                if self.page.locator("input[name='remember']").count() > 0:
                    self.page.check("input[name='remember']")
            except: pass
            
            # Submit
            if self.page.locator("button:has-text('Login')").count() > 0:
                self.page.click("button:has-text('Login')")
            elif self.page.locator("input[type='submit']").count() > 0:
                self.page.click("input[type='submit']")
            else:
                self.page.keyboard.press("Enter")
            
            try:
                self.page.wait_for_load_state("networkidle", timeout=15000)
            except: pass
            time.sleep(5)
            
            if self.page.locator("a:has-text('Logout')").count() > 0 or "motorcalc.php" in self.page.url:
                print("Login successful.")
                return True
            else:
                print("WARNING: Login might have failed. (No Logout link found)")
        except Exception as e:
            print(f"Login error: {e}")
        return False

    def _ensure_session_valid(self):
        """Checks if session is still valid and re-logs in if necessary."""
        try:
            # Wait for any active navigation/redirection
            self.page.wait_for_load_state("load", timeout=5000)
            
            # Check for logout/login indicators
            is_logged_in = self.page.locator("a:has-text('Logout')").count() > 0
            is_login_page = "login.php" in self.page.url or "loggedout" in self.page.url
            has_login_form = self.page.locator("input[name='username']").count() > 0
            
            if is_login_page or (not is_logged_in and has_login_form):
                print("Session invalid or Login page detected. Re-logging in...")
                return self.login(self.email, self.password)
            
            # Check for URL-based redirect (login.php?target)
            # Example: https://www.ecalc.ch/calcmember/login.php?https://www.ecalc.ch/setupfinder.php
            if "login.php?" in self.page.url:
                try:
                    parts = self.page.url.split("login.php?")
                    if len(parts) > 1 and parts[1].startswith("http"):
                        target = parts[1]
                        # Check login status
                        is_logged_in_now = self.page.locator("a:has-text('Logout')").count() > 0
                        
                        if self.logged_in_alert_seen or is_logged_in_now:
                            print(f"Logged in. Following detected redirect to: {target}")
                            self.page.goto(target)
                            time.sleep(2)
                            return True
                except Exception as e:
                    print(f"Error handling dynamic redirect: {e}")

            # Ambiguous state (neither logged in nor login form)
            if not is_logged_in and not has_login_form:
                if self.logged_in_alert_seen:
                    print("Logged-in alert was seen recently. Assuming valid session.")
                    # Force nav to tool if not there
                    if "motorcalc.php" not in self.page.url:
                         self.page.goto("https://www.ecalc.ch/motorcalc.php")
                    return True

                print("Ambiguous session state. Checking for Member Landing Page...")
                # Check if we are on the landing page which often has ID 'member_content' or links to calculators
                if self.page.locator("a[href*='motorcalc.php']").count() > 0:
                     print("Found PropCalc link. We are logged in. Navigating...")
                     try:
                         self.page.goto("https://www.ecalc.ch/motorcalc.php")
                         return True
                     except: pass
                
                print("Waiting 3s...")
                time.sleep(3)
                # Quick re-check
                if self.page.locator("a:has-text('Logout')").count() > 0: return True
                
                # If still failing, reload
                print("Reloading to check session...")
                self.page.reload()
                time.sleep(3)
                if self.page.locator("a:has-text('Logout')").count() > 0: return True

            return True
        except Exception as e:
            # print(f"Non-critical error checking session: {e}")
            return True # Assume OK or will be caught by next action

    def run_setup_finder(self, inputs: Dict[str, str], limit: int = 10) -> List[Dict[str, Any]]:
        print("Running Setup Finder...")
        self.page.goto("https://www.ecalc.ch/setupfinder.php")
        # Patience: allow page to settle and any session alerts to fire
        time.sleep(5)
        self.page.wait_for_load_state("networkidle", timeout=10000)
        
        # Verify we are still on the right page (in case of redirection)
        if "setupfinder.php" not in self.page.url:
            print("Redirected from Setup Finder. Attempting to return...")
            self.page.goto("https://www.ecalc.ch/setupfinder.php")
            time.sleep(2)

        # Field Mapping
        mapping = {
            "weight": "inAcAuw",
            "wingspan": "inAcSpan",
            "wing_area": "inGWingArea",
            "speed": "inPerfSpeed",
            "thrust": "inPerfThrust",
            "flight_time": "inPerfTime",
            "battery_cells": "inBS", 
            "battery_voltage": "inBCellV",
            "motors": "inGMotors",
            "max_weight": "inMWeightMax",
            "max_prop_diameter": "inPDiameter",
            "prop_blades": "inPBlades",
            "elevation": "inGElevation",
            "temperature": "inGTemp",
        }

        if "flight_plan" in inputs:
             print(f"Selecting Flight Plan: {inputs['flight_plan']}")
             try:
                self.page.select_option("#inPerfMission", label=inputs["flight_plan"])
                # Wait a bit for recommendations to settle
                time.sleep(1)
             except Exception as e:
                print(f"Error selecting Flight Plan: {e}")

        if "wing_type" in inputs:
             try:
                 self.page.wait_for_selector("#inAcWingTyp", timeout=5000)
                 self.page.select_option("#inAcWingTyp", value=str(inputs["wing_type"]))
             except Exception as e:
                 print(f"Error selecting Wing Type: {e}")

        # Fill text inputs (AFTER flight plan to avoid overwrite)
        for key, val in inputs.items():
            if key in mapping:
                selector = f"#{mapping[key]}"
                try:
                    # Wait for each field to ensure they are ready
                    self.page.wait_for_selector(selector, timeout=5000)
                    print(f"Filling {key}: {val}")
                    # Use sequence to ensure JS handlers triggers
                    self.page.locator(selector).focus()
                    self.page.fill(selector, str(val))
                    self.page.locator(selector).press("Tab")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"Warning: Could not fill {key} ({selector}): {e}")

        # Handle Interstitials (Cookies / Modals)
        print("Checking for overlays...")
        try:
            # Cookies
            if self.page.locator(".cookieinfo-close").count() > 0:
                print("Closing Cookie Info...")
                self.page.click(".cookieinfo-close")
                time.sleep(0.5)
                
            # Modal Confirm (Terms/Upgrade)
            if self.page.locator("#modalConfirm").is_visible():
                print("Accepting Modal Confirm...")
                self.page.click("#modalConfirmOk")
                time.sleep(1)
            # Generic retry for stability
            self.page.wait_for_load_state("networkidle", timeout=5000)
        except Exception as e:
            # print(f"Error handling overlays: {e}")
            pass

        # Click Calculate/Search
        print("Clicking Search...")
        clicked = False
        try:
            # Target the element with the onclick=calculate trigger
            search_btn = self.page.locator("span[onclick*='calculate']").first
            if search_btn.count() > 0:
                print("Clicked calculate button")
                search_btn.click()
                clicked = True
            elif self.page.locator("#btnFindSetup").count() > 0:
                print("Clicked #btnFindSetup parent")
                self.page.locator("#btnFindSetup").locator("xpath=..").click()
                clicked = True
            else:
                print("Trying fallback submit button...")
                btn = self.page.locator("button:has-text('Calculate'), input[type='submit']")
                if btn.count() > 0:
                    btn.first.click()
                    clicked = True
        except Exception as e:
            print(f"Error clicking search: {e}")
        
        if not clicked:
            print("Failed to click any search button. Dumping page.")
            with open("debug_setupfinder_nobtn.html", "w", encoding="utf-8") as f:
                f.write(self.page.content())
            return []
        
        print("Waiting for results (20s)...")
        time.sleep(20) # Wait for results
        
        # Verify if results are present in DOM
        content = self.page.content()
        if "recid" not in content:
            print("WARNING: 'recid' not found in page content after 20s. Results might be empty or still loading.")
            # Take a screenshot if possible? No, but we can dump HTML
            with open("debug_setupfinder_noresults.html", "w", encoding="utf-8") as f:
                f.write(content)
        
        # Extract Results
        results = []
        seen_setups = set()  # Key: (motor_id, prop_diam, prop_pitch)
        
        page_num = 1
        while len(results) < limit:
            rows = self.page.locator("table tr[recid]").all() # recid only matches data rows
            print(f"Page {page_num}: Found {len(rows)} potential result rows.")
            
            new_on_this_page = 0
            for i, row in enumerate(rows):
                if len(results) >= limit: break
                
                # Extract metadata from the 'title' attribute of the cell with col="12"
                metadata_cell = row.locator('td[col="12"] div')
                if metadata_cell.count() == 0:
                    continue
                
                title = metadata_cell.get_attribute("title")
                if not title or "," not in title:
                    continue
                    
                vals = [v.strip() for v in title.split(",")]
                if len(vals) < 5: # Minimal: diam, pitch, manuf_id, motor_id, kv
                    print(f"Skipping row {i}: too few metadata values ({len(vals)})")
                    continue
                
                # Robust Mapping using search from the end (since beginning is variable)
                manuf_name = "Unknown"
                manuf_idx = -1
                # 1. Find Manufacturer (skipping version at -1 typically)
                for j in range(len(vals)-1, 1, -1):
                    v_low = vals[j].lower()
                    # Known brands to help anchor the search
                    if any(brand in v_low for brand in ["t-motor", "sunnysky", "scorpion", "mad", "neu", "leo", "dual", "joker", "cobra", "antigravity", "u-series"]):
                        manuf_name = vals[j]
                        manuf_idx = j
                        break
                
                # 2. Find Drive Weight (first large numeric before manufacturer or from expected position)
                drive_weight = "N/A"
                if manuf_idx > 0:
                    for j in range(manuf_idx - 1, 0, -1):
                        v = vals[j]
                        if v.replace('.', '', 1).isdigit() and float(v) > 50:
                            drive_weight = v
                            break
                if drive_weight == "N/A" and len(vals) >= 12:
                    # Fallback to standard position 11 (0-indexed)
                    v = vals[11]
                    if v.replace('.', '', 1).isdigit():
                        drive_weight = v
                
                # 3. Basic fields are usually at the beginning
                motor_id = vals[3] if len(vals) > 3 else "Unknown"
                
                setup_key = (motor_id, vals[0], vals[1]) # Unique combination
                if setup_key in seen_setups:
                    continue

                data = {
                    "prop_diam": vals[0],
                    "prop_pitch": vals[1],
                    "manufacturer_id": vals[2],
                    "motor_id": motor_id,
                    "motor_kv": vals[4] if len(vals) > 4 else "?",
                    "motor_name": f"{manuf_name} {motor_id}" if manuf_name != "Unknown" else motor_id,
                    "manufacturer": manuf_name,
                    "drive_weight": drive_weight
                }
                
                results.append(data)
                seen_setups.add(setup_key)
                new_on_this_page += 1
            
            print(f"Extracted {new_on_this_page} new setups from page {page_num}.")
            
            if len(results) >= limit:
                print(f"Reached limit of {limit} results.")
                break
                
            # Scroll to load more results using Keyboard which triggers events better
            print(f"Scrolling... (Page {page_num})")
            try:
                # 1. Focus the grid or body
                if page_num == 1:
                    try:
                        # Try to click the last row to focus grid?
                        if rows:
                            rows[-1].click(timeout=1000)
                        else:
                            self.page.click(".w2ui-grid-records", timeout=1000)
                    except:
                        self.page.click("body")
                
                # 2. Press PageDown multiple times
                for _ in range(5):
                    self.page.keyboard.press("PageDown")
                    time.sleep(0.1)
                
                # 3. JS Scroll Fallback
                self.page.evaluate("""() => {
                    var grid = document.querySelector('.w2ui-grid-records');
                    if (grid) {
                        grid.scrollTop += grid.clientHeight * 2;
                    } else {
                        window.scrollBy(0, window.innerHeight * 2);
                    }
                }""")
                
                # Wait for refresh
                time.sleep(2.0)
                
            except Exception as e:
                print(f"Error during scroll: {e}")
                break
            
            page_num += 1
            if new_on_this_page == 0:
                 # consecutive empty scans
                 print("No new items found after scroll. Trying 'End' key once...")
                 self.page.keyboard.press("End")
                 time.sleep(2)
                 
                 # Check strict staleness (if we really didn't find anything for 2 cycles)
                 if page_num > 100: break # Safety break
                 
        print(f"Total extracted: {len(results)} valid setups.")
        return results

    def filter_setups(self, setups: List[Dict[str, Any]], target_diam: float, manufacturer: str) -> List[Dict[str, Any]]:
        """
        Fast filtering of motors based on Prop Diameter and Manufacturer.
        - target_diam: e.g. 18.0 for "18x10.0"
        - manufacturer: string to match in manufacturer or motor name (case insensitive)
        """
        filtered = []
        clean_manuf = manufacturer.lower()
        
        print(f"Filtering {len(setups)} setups for Diam~={target_diam} and Manuf='{manufacturer}'")
        
        for s in setups:
            # 1. Filter by Manufacturer
            s_manuf = s.get("manufacturer", "").lower()
            s_motor = s.get("motor_name", "").lower()
            if clean_manuf not in s_manuf and clean_manuf not in s_motor:
                continue
                
            # 2. Filter by Diameter
            # Format typically "18x10.0" or "18.0x..."
            raw_diam = s.get("prop_diam", "")
            try:
                # Extract the leading number before 'x' or ' '
                if "x" in raw_diam:
                    d_str = raw_diam.split("x")[0].strip()
                elif " " in raw_diam:
                    d_str = raw_diam.split(" ")[0].strip()
                else:
                    d_str = raw_diam
                
                d_val = float(d_str)
                
                # Allow small tolerance (e.g. 18.0 vs 18)
                if abs(d_val - target_diam) < 0.1:
                    filtered.append(s)
            except:
                # If parsing fails, skip or check if strict match needed
                continue
                
        return filtered

    def run_prop_calc(self, setup_data: Dict[str, Any]) -> Dict[str, str]:
        print(f"Running Prop Calc for {setup_data.get('motor_name', 'Unknown')}...")
        
        # Initialize results early so it's always available in except/return blocks
        results = {
            "motor": setup_data.get("motor_name", "Unknown"),
            "motor_weight": "N/A",
            "drive_weight": setup_data.get("drive_weight", "N/A"),
            "manufacturer": setup_data.get("manufacturer", ""),
            "prop_diam": setup_data.get("prop_diam", setup_data.get("max_prop_diameter", "?")), 
            "prop_pitch": setup_data.get("prop_pitch", "?"),
            "prop_blades": setup_data.get("prop_blades", "2"),
            "power": "N/A",
            "traction": "N/A"
        }
        print(f"DEBUG: results initialized: {results}")

        for attempt in range(2):
            try:
                # Ensure session is valid
                if not self._ensure_session_valid():
                    print(f"Failed to ensure session for {results['motor']}")
                    continue
                
                # Navigate if not already on the right page
                if "motorcalc.php" not in self.page.url:
                    print(f"PropCalc attempt {attempt+1}: Navigating to motorcalc.php...")
                    self.page.goto("https://www.ecalc.ch/motorcalc.php", timeout=60000)
                    time.sleep(2)
                
                # Double check navigation (handle landing page redirects)
                if "calcmember/index.php" in self.page.url or "calcmember/login.php" in self.page.url:
                    print("On landing/login page. Attempting direct navigation to MotorCalc...")
                    try:
                        # Try clicking the link first as it often sets session cookies/state better than direct URL
                        if self.page.locator("a[href*='motorcalc.php']").count() > 0:
                            self.page.click("a[href*='motorcalc.php']")
                        else:
                            self.page.goto("https://www.ecalc.ch/motorcalc.php", timeout=60000)
                        
                        time.sleep(3)
                        
                        # Handle the Alert if it pops up again
                        # The dialog handler should take care of it, but we might need to wait
                    except Exception as e:
                        print(f"Nav error: {e}")
                
                # If still on landing page, try force
                if "calcmember" in self.page.url:
                     print("Still on landing page. Forcing URL...")
                     self.page.goto("https://www.ecalc.ch/motorcalc.php", wait_until="domcontentloaded")
                     time.sleep(2)

                # Check for form stability
                try:
                    self.page.wait_for_selector("#inMType", timeout=10000)
                except:
                    if "motorcalc.php" not in self.page.url:
                         print(f"Not on motorcalc.php (URL: {self.page.url}). Retrying navigation...")
                         self.page.goto("https://www.ecalc.ch/motorcalc.php")
                    else:
                         print("MotorCalc elements not found on page. Reloading...")
                         self.page.reload()
                    self.page.wait_for_selector("#inMType", timeout=15000)

                # 1. Select Manufacturer
                manuf_id = setup_data.get("manufacturer_id")
                manuf_name = setup_data.get("manufacturer")
                
                if manuf_id or manuf_name:
                    try:
                        manuf_sel = "#inMManufacturer"
                        if manuf_id:
                            print(f"Selecting Manufacturer by ID: {manuf_id} ({manuf_name})")
                            self.page.select_option(manuf_sel, value=str(manuf_id))
                        else:
                            print(f"Selecting Manufacturer by Label: {manuf_name}")
                            self.page.select_option(manuf_sel, label=manuf_name)
                        
                        # Wait for AJAX update
                        self.page.wait_for_load_state("networkidle")
                        # Also wait for the motor list to be populated
                        try:
                            self.page.wait_for_function("document.querySelector('#inMType').options.length > 1", timeout=8000)
                        except:
                            print("Motor list did not populate. Retrying manufacturer selection...")
                            if manuf_id:
                                self.page.select_option(manuf_sel, value=str(manuf_id))
                            else:
                                self.page.select_option(manuf_sel, label=manuf_name)
                            time.sleep(2)
                    except Exception as e:
                        print(f"Manuf select error: {e}")
                        pass
                 
                # 2. Select Motor with WAIT loop
                motor_name = setup_data.get('motor_name')
                motor_id = setup_data.get('motor_id')
                target_motor = motor_id if motor_id else motor_name

                if target_motor:
                    print(f"Selecting Motor: {target_motor}")
                    
                    found = False
                    # 1. Try exact match with motor_id or motor_name as label
                    for label_try in [motor_id, motor_name]:
                        if not label_try: continue
                        try:
                            self.page.select_option("#inMType", label=label_try)
                            found = True
                            break
                        except: pass
                    
                    if not found:
                        print(f"Exact match failed. Finding alternative for '{target_motor}'...")
                        # Get all options with their 'disabled' status
                        options_data = self.page.evaluate("""() => {
                            var sel = document.getElementById('inMType');
                            if (!sel) return [];
                            var res = [];
                            for (var i = 0; i < sel.options.length; i++) {
                                res.push({
                                    text: sel.options[i].text,
                                    value: sel.options[i].value,
                                    disabled: sel.options[i].disabled
                                });
                            }
                            return res;
                        }""")
                        
                        target_kv = str(setup_data.get('motor_kv', ''))
                        clean_target = target_motor.lower()
                        
                        matches = []
                        for opt in options_data:
                            opt_text = opt["text"].lower()
                            # Logic: If target matches AND (KV match OR no target KV)
                            if clean_target in opt_text:
                                score = 1
                                if target_kv and (f"({target_kv})" in opt_text or f"kv{target_kv}" in opt_text):
                                    score = 10 # Strong match
                                matches.append((score, opt))
                        
                        if matches:
                            # Sort by score descending
                            matches.sort(key=lambda x: x[0], reverse=True)
                            best_match = matches[0][1]
                            
                            if best_match["disabled"]:
                                print(f"WARNING: Motor '{best_match['text']}' is FOUND but DISABLED. (Member only / Access restricted?)")
                            else:
                                try:
                                    self.page.select_option("#inMType", value=best_match["value"])
                                    found = True
                                    print(f"Selected match: {best_match['text']}")
                                except Exception as e:
                                    print(f"Failed to select best match: {e}")
                        
                        if not found:
                             print("Motor not found in list even with search logic.")
                             
                    # VERIFY Selection
                    time.sleep(0.5)
                    val = self.page.eval_on_selector("#inMType", "el => el.options[el.selectedIndex].text")
                    if target_motor not in val and (motor_id and motor_id not in val):
                        print(f"WARNING: Motor selection might have failed. Current value in dropdown: {val}")
                
                time.sleep(1)

                # Prop
                if "prop_diam" in setup_data:
                     self.page.fill("#inPDiameter", setup_data["prop_diam"].replace(",", "."))
                if "prop_pitch" in setup_data:
                     self.page.fill("#inPPitch", setup_data["prop_pitch"].replace(",", "."))

                # Select Prop Type
                if "prop_type" in setup_data:
                    p_type = setup_data["prop_type"]
                    print(f"Selecting Prop Type: {p_type}")
                    try:
                        self.page.select_option("#inPType", label=p_type)
                    except:
                        # Fallback partial match
                         try:
                            options = self.page.locator("#inPType option").all_inner_texts()
                            for opt in options:
                                if p_type.lower() in opt.lower():
                                    self.page.select_option("#inPType", label=opt)
                                    print(f"Selected Prop Type (Partial): {opt}")
                                    break
                         except Exception as e:
                             print(f"Prop Type selection failed: {e}")

                # Select ESC
                esc_model = setup_data.get("esc", "max 100A")
                print(f"Selecting ESC: {esc_model}")
                try:
                    self.page.select_option("#inEType", label=esc_model)
                except Exception as e:
                    print(f"ESC Selection Failed: {e}. Trying partial match...")
                    try:
                        # Fallback: Find option containing text
                        options = self.page.locator("#inEType option").all_inner_texts()
                        for opt in options:
                            if esc_model.lower() in opt.lower():
                                self.page.select_option("#inEType", label=opt)
                                print(f"Selected ESC (Partial): {opt}")
                                break
                    except:
                        print("Could not select ESC.")

                # Select Battery Model
                bat_model = setup_data.get("battery_model", "LiPo 3300mAh - 45/60C") 
                print(f"Selecting Battery: {bat_model}")
                try:
                    self.page.select_option("#inBCell", label=bat_model)
                except:
                    # Fallback logic for battery
                    print(f"Battery Selection Failed for '{bat_model}'. Trying partial match...")
                    try:
                        options = self.page.locator("#inBCell option").all_inner_texts()
                        for opt in options:
                            if bat_model.lower() in opt.lower():
                                self.page.select_option("#inBCell", label=opt)
                                print(f"Selected Battery (Partial): {opt}")
                                break
                    except:
                         print("Could not select Battery.")
                         
                # Battery Handling (Capacity manually if needed, but selecting model often sets it)
                try:
                    # If Capacity is disabled, ensure we are in Custom battery mode?
                    # eCalc might lock fields if a specific battery is selected (default).
                    pass
                except: pass
                
                # Filled Weight
                if "weight" in setup_data:
                    print(f"Setting Weight: {setup_data['weight']}g")
                    try:
                        self.page.fill("#inGWeight", str(setup_data["weight"]))
                    except Exception as e:
                        print(f"Error setting weight: {e}")

                # Filled Battery Cells
                if "battery_cells" in setup_data:
                     # Ensure we just pass the number
                     val = str(setup_data["battery_cells"])
                     print(f"Setting Battery Cells: {val}S")
                     try:
                        self.page.fill("#inBS", val)
                     except Exception as e:
                        print(f"Error setting battery cells: {e}")

                # Select Battery Charge State
                if "battery_charge_state" in setup_data:
                    charge_state = setup_data["battery_charge_state"]
                    print(f"Setting Charge State: {charge_state}")
                    try:
                        self.page.select_option("#inBChargeState", label=charge_state)
                    except Exception as e:
                        print(f"Error setting charge state: {e}")

                if "bat_cap" in setup_data:
                     try:
                        if self.page.locator("#inBCellCap").is_enabled():
                            cap_val = setup_data["bat_cap"].replace(",", ".")
                            self.page.fill("#inBCellCap", cap_val)
                     except Exception as e:
                        print(f"B.Cap error: {e}")

                if "bat_c" in setup_data:
                     try:
                        if self.page.locator("#inBCcont").is_enabled():
                             self.page.fill("#inBCcont", setup_data["bat_c"].replace(",", "."))
                     except: pass
                     
                # FORCE UPDATE of form fields if they are reset by JS
                # Sometimes checking if the value stuck is useful
                if "prop_diam" in setup_data:
                    curr = self.page.input_value("#inPDiameter")
                    target = setup_data["prop_diam"].replace(",", ".")
                    if curr != target:
                        print(f"Refilling Prop Diam (was {curr}, want {target})")
                        self.page.fill("#inPDiameter", target)

                # TRIGGER CALCULATION
                print("Triggering Calculation...")
                # We use JS directly because the button selector is elusive
                self.page.evaluate("calculate()")
                
                # Check Success - Wait for 'outTotPout' to have a numeric value
                # Max wait 15s instead of 5s
                print("Waiting for calculation results...")
                calc_success = False
                for _ in range(30):
                    val = self.page.locator("#outTotPout").inner_text().strip()
                    if val and val != "-" and val != "" and val != "0":
                        calc_success = True
                        break
                    time.sleep(0.5)
                 
                if not calc_success:
                    print("Calculation failed (Results timed out or empty). Proceeding with weight extraction...")
                    # return {"power": "N/A", "traction": "N/A", "motor": setup_data.get("motor_name")}
                
                # Update results from PropCalc page
                try:
                    # Power: User expects Max Power (Input) usually. 
                    # outMaxWin is max electrical power in. outOptWin is optimal.
                    pwr_selectors = ["#outMaxWin", "#outOptWin", "#outTotPout"]
                    for sel in pwr_selectors:
                        if self.page.locator(sel).count() > 0:
                            val = self.page.locator(sel).inner_text().strip()
                            if val and val != "-" and val != "0":
                                results["power"] = val
                                break
                    
                    # Mass (Drive Weight/Massa GMP): outTotDriveWeight is the most accurate
                    if self.page.locator("#outTotDriveWeight").count() > 0:
                        results["drive_weight"] = self.page.locator("#outTotDriveWeight").inner_text().strip()
                except: pass
                
                # Double check Diam/Pitch from input if they are '?' or missing in setup_data
                if results.get("prop_diam") in ["?", None]:
                    try:
                        results["prop_diam"] = self.page.locator("#inPDiameter").input_value()
                    except: pass
                if results.get("prop_pitch") in ["?", None]:
                    try:
                        results["prop_pitch"] = self.page.locator("#inPPitch").input_value()
                    except: pass


                # 1. Motor Weight
                try:
                    # eCalc IDs: outMWeight (calculated weight of motor), or from setup finder input
                    if self.page.locator("#outMWeight").count() > 0:
                        results["motor_weight"] = self.page.locator("#outMWeight").inner_text().strip()
                    elif self.page.locator("#inMWeight").count() > 0:
                         results["motor_weight"] = self.page.locator("#inMWeight").input_value().strip()
                    else:
                        results["motor_weight"] = "N/A"
                except:
                    results["motor_weight"] = "N/A"

                # 2. Power (already extracted above)
                
                # 3. Speed Sweep (0 to 135 step 9)
                # Static Traction (Speed 0) - usually calculated at speed 0 input
                # Ensure input is 0 first? defaulting usually 0.
                
                speeds = list(range(0, 136, 9)) # 0, 9, 18 ... 135
                
                print(f"Running Speed Sweep: {speeds} km/h")
                for v in speeds:
                    try:
                        # Set speed
                        self.page.fill("#inPSpeed", str(v))
                        # Trigger Calc
                        self.page.evaluate("calculate()")
                        
                        # Wait for update
                        time.sleep(0.8) 
                        
                        # Extract Traction
                        if self.page.locator("#outPFlightThrust").count() > 0:
                            trac = self.page.locator("#outPFlightThrust").inner_text().strip()
                        else:
                            trac = "N/A"
                            
                        results[f"traction_{v}"] = trac
                    except Exception as ev:
                        print(f"Error at speed {v}: {ev}")
                        results[f"traction_{v}"] = "Error"
                
                # 4. Efficiency Analysis (Parse #rpmDynTable)
                # Set speed to 0 for static efficiency calculations
                try:
                    self.page.fill("#inPSpeed", "0")
                    self.page.evaluate("calculate()")
                    time.sleep(0.8)
                    print("Speed set to 0 for efficiency analysis")
                except Exception as e:
                    print(f"Error setting speed to 0: {e}")
                
                # Ensure table is visible and populated
                try:
                    self.page.wait_for_selector("#rpmDynTable tr", timeout=5000)
                except:
                    print("Efficiency Table (#rpmDynTable) not found or slow.")
                
                target_power = setup_data.get("analyzed_power", 600)
                
                try:
                    eff_data = self.page.evaluate("""(target_power) => {
                        var table = document.getElementById('rpmDynTable');
                        if (!table) return {error: "Table not found"};
                        
                        var rows = [];
                        // Skip header (row 0) and units (row 1)? snippet implies headers are tr.
                        // We iterate all trs.
                        var trs = table.getElementsByTagName('tr');
                        
                        for (var i = 2; i < trs.length; i++) {
                            var cells = trs[i].getElementsByTagName('td');
                            if (cells.length < 8) continue;
                            
                            // Cell indices based on snippet:
                            // 3: Throttle % (16, 21...)
                            // 6: Power W (70.1, 118.3...)
                            // 7: Efficiency % (53, 82...)
                            
                            var thr = parseFloat(cells[3].innerText);
                            var pwr = parseFloat(cells[6].innerText);
                            var eff = parseFloat(cells[7].innerText);
                            var thrst = parseFloat(cells[8].innerText);
                            
                            if (!isNaN(thr)) {
                                rows.push({throttle: thr, power: pwr, eff: eff, thrust: thrst});
                            }
                        }
                        
                        if (rows.length === 0) return {error: "No data rows"};
                        
                        // 1. Max Throttle
                        var maxThrRow = rows[rows.length - 1]; // Last row
                        
                        // 2. Target Power
                        var closestRow = rows[0];
                        var minDiff = Math.abs(rows[0].power - target_power);
                        
                        for (var i = 1; i < rows.length; i++) {
                            var diff = Math.abs(rows[i].power - target_power);
                            if (diff < minDiff) {
                                minDiff = diff;
                                closestRow = rows[i];
                            }
                        }
                        
                        return {
                            eff_max_throttle: maxThrRow.eff,
                            max_throttle_val: maxThrRow.throttle,
                            eff_at_power: closestRow.eff,
                            power_at_eff: closestRow.power,
                            throttle_at_power: closestRow.throttle,
                            thrust_at_power: closestRow.thrust
                        };
                    }""", target_power)
                    
                    if "error" not in eff_data:
                        results["eff_max_throttle"] = str(eff_data.get("eff_max_throttle", "N/A"))
                        results["eff_at_power"] = str(eff_data.get("eff_at_power", "N/A"))
                        results["power_at_eff"] = str(eff_data.get("power_at_eff", "N/A"))
                        results["thr_at_power"] = str(eff_data.get("throttle_at_power", "N/A"))
                        results["thrust_at_power"] = str(eff_data.get("thrust_at_power", "N/A"))
                    else:
                        results["eff_max_throttle"] = "Err"
                        results["eff_at_power"] = "Err"
                        results["thr_at_power"] = "Err"
                        results["thrust_at_power"] = "Err"
                        
                except Exception as e:
                    print(f"Error extracting efficiency table: {e}")
                    results["eff_max_throttle"] = "Err"
                    results["eff_at_power"] = "Err"

                return results
                
            except Exception as e:
                print(f"Error in PropCalc (Attempt {attempt+1}): {e}")
                # ... (retry logic)
                if self._ensure_session_valid():
                    continue 
                if attempt == 1:
                     try:
                        with open("debug_propcalc_error.html", "w", encoding="utf-8") as f:
                            f.write(self.page.content())
                     except: pass
                     return results
                     
        return results
