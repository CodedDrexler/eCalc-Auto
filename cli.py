import sys
import time
import json
import csv
import os
import argparse
from rich.console import Console
from rich.prompt import Prompt, IntPrompt, FloatPrompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint

from automation import ECalAutomator

console = Console()

def get_resource_base():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_output_dir():
    path = os.path.join(os.path.expanduser("~"), "eCalc Auto")
    os.makedirs(path, exist_ok=True)
    return path

def load_credentials():
    email = os.getenv("ECALC_EMAIL")
    password = os.getenv("ECALC_PASSWORD")
    if email and password:
        return {"email": email, "password": password}
    candidates = [
        os.path.join(get_output_dir(), "credentials.json"),
        os.path.join(get_resource_base(), "credentials.json"),
    ]
    for path in candidates:
        try:
            with open(path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            continue
    console.print(f"[red]credentials.json not found in {candidates}![/red]")
    sys.exit(1)

def main():
    os.system('cls')
    console.clear()
    
    # Parse Arguments
    parser = argparse.ArgumentParser(description="eCalc Automation Tool")
    parser.add_argument("-A", "--auto", action="store_true", help="Run automatically with default/last settings")
    args = parser.parse_args()
    
    # Header
    console.print(Panel.fit(
        "[bold cyan]eCalc Automation Tool[/bold cyan]\n"
        "[dim]Automated Setup Finder & PropCalc Extraction[/dim]",
        border_style="cyan"
    ))
    
    # Load Default Settings
    base_dir = get_resource_base()
    defaults = {}
    try:
        path = os.path.join(base_dir, "default_settings.json")
        with open(path, "r", encoding="utf-8") as f:
            defaults = json.load(f)
    except FileNotFoundError:
        # Fallback defaults if file missing
        defaults = {
            "weight": 18000, "wingspan": 3900, "wing_area": 190.3, "speed": 1, "thrust": 5000,
            "battery_cells": 6, "limit": 1, "esc_model": "max 90A", 
            "battery_model": "LiPo 3300mAh - 45/60C", "flight_plan": "3D - heavy",
            "flight_time": 3, "elevation": 650, "max_prop_diameter": 20,
            "prop_blades": 2, "max_motor_weight_pct": 6, "close_browser": "y",
            "analyzed_power": 600, "battery_charge_state": "cheia", "prop_type": "APC Electric E"
        }

    # Helper function to get input or default
    def get_input(prompt_cls, msg, key, default_val=None, **kwargs):
        val = defaults.get(key, default_val)
        if args.auto:
            return val
        return prompt_cls.ask(msg, default=val, **kwargs)

    # Inputs
    rprint("[bold yellow]\nSTEP 1: Flight Configuration[/bold yellow]")
    if args.auto:
        rprint("[cyan]Running in AUTOMATIC mode (-A). Using default values...[/cyan]")
    
    weight = get_input(IntPrompt, "   [green]Total Weight (g)[/green]", "weight", 18000)
    wingspan = get_input(IntPrompt, "   [green]Wingspan (mm)[/green]", "wingspan", 3900)
    wing_area = get_input(FloatPrompt, "   [green]Wing Area (dm²)[/green]", "wing_area", 190.3)
    
    flight_plan = get_input(Prompt, "   [green]Flight Plan[/green]", "flight_plan", "3D - heavy")
    flight_time = get_input(IntPrompt, "   [green]Flight Time (min)[/green]", "flight_time", 3)
    elevation = get_input(IntPrompt, "   [green]Elevation (m)[/green]", "elevation", 650)
    
    speed = get_input(IntPrompt, "   [green]Desired Speed (km/h)[/green]", "speed", 1)
    thrust = get_input(IntPrompt, "   [green]Desired Thrust (g)[/green]", "thrust", 5000)

    max_motor_weight_pct = get_input(IntPrompt, "   [green]Max Motor Weight (%)[/green]", "max_motor_weight_pct", 6)
    analyzed_power = get_input(IntPrompt, "   [green]Analyzed Power (W)[/green]", "analyzed_power", 600)
    battery_cells = get_input(IntPrompt, "   [green]Battery Cells (S)[/green]", "battery_cells", 6)
    
    battery_charge_state = get_input(Prompt, "   [green]Battery Charge State[/green]", "battery_charge_state", "cheia", choices=["cheia", "normal", "baixa"])
    
    max_prop_diameter = get_input(IntPrompt, "   [green]Max Prop Diameter (inch)[/green]", "max_prop_diameter", 20)
    prop_blades = get_input(IntPrompt, "   [green]Prop Blades[/green]", "prop_blades", 2)
    prop_type = get_input(Prompt, "   [green]Prop Type[/green]", "prop_type", "APC Electric E")
    
    limit = get_input(IntPrompt, "   [green]Max Setups to Analyze[/green]", "limit", 1)
    esc_model = get_input(Prompt, "   [green]ESC Model[/green]", "esc_model", "max 90A")
    battery_model = get_input(Prompt, "   [green]Battery Model[/green]", "battery_model", "LiPo 3300mAh - 45/60C")
    close_browser = get_input(Prompt, "   [green]Close Browser after finish?[/green]", "close_browser", "y", choices=["y", "n"])

    # Manufacturer Filter
    default_manuf = ", ".join(defaults.get("manufacturers_filter", ["T-Motor", "SunnySky", "Scorpion"]))
    if args.auto:
        manuf_filter_str = default_manuf
    else:
        manuf_filter_str = Prompt.ask("   [green]Manufacturer Filter (comma sep, or 'all')[/green]", default=default_manuf)
    
    # Prop Diameter Filter (Exact Match)
    target_diam_filter = None
    if not args.auto:
        diam_input = Prompt.ask("   [green]Target Prop Diameter Filter (e.g. 18, or 'all')[/green]", default="all")
        if diam_input.lower() != "all":
            try:
                target_diam_filter = float(diam_input)
            except ValueError:
                rprint("[red]Invalid diameter. Ignoring filter.[/red]")

    # Confirmation
    rprint("\n[bold]Configuration Summary:[/bold]")
    if args.auto:
        confirm = "y"
    
    rprint(f" • Weight: {weight}g")
    rprint(f" • Wingspan: {wingspan}mm")
    rprint(f" • Area: {wing_area}dm²")
    rprint(f" • Flight Plan: {flight_plan}")
    rprint(f" • Flight Time: {flight_time}min")
    rprint(f" • Elevation: {elevation}m")
    rprint(f" • Speed: {speed}km/h")
    rprint(f" • Thrust: {thrust}g")
    rprint(f" • Max Motor Weight: {max_motor_weight_pct}%")
    rprint(f" • Analyzed Power: {analyzed_power}W")
    rprint(f" • Battery: {battery_cells}S")
    rprint(f" • Charge State: {battery_charge_state}")
    rprint(f" • Max Prop: {max_prop_diameter}\"")
    rprint(f" • Blades: {prop_blades}")
    rprint(f" • Prop Type: {prop_type}")
    rprint(f" • Limit: {limit} motors")
    rprint(f" • ESC: {esc_model}")
    rprint(f" • Battery Model: {battery_model}")
    rprint(f" • Close Browser: {'Yes' if close_browser == 'y' else 'No'}")
    rprint(f" • Manufacturers Info: {manuf_filter_str}")
    rprint(f" • Diam Filter: {target_diam_filter if target_diam_filter else 'ALL'}")
    
    if not args.auto:
        if not Prompt.ask("\n[bold]Ready to calculate?[/bold]", choices=["y", "n"], default="y") == "y":
            console.print("[red]Aborted.[/red]")
            sys.exit(0)

    # Initialize Automation
    os.system('cls')
    console.clear()
    console.print("\n[bold yellow]STEP 2: Automation[/bold yellow]")
    
    auto = ECalAutomator(headless=False)
    
    try:
        with Progress(
            SpinnerColumn("dots", style="bold cyan"),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            task = progress.add_task("Initializing Browser...", total=None)
            auto.start()
            
            creds = load_credentials()
            progress.update(task, description=f"Logging in as {creds['email']}...")
            auto.login(creds['email'], creds['password'])
            
            progress.update(task, description="Running Setup Finder (this takes ~10s)...")
            inputs = {
                "weight": str(weight),
                "wingspan": str(wingspan),
                "wing_area": str(wing_area),
                "speed": str(speed),
                "thrust": str(thrust),
                "max_weight": str(max_motor_weight_pct),
                "battery_cells": str(battery_cells),
                "wing_type": "Monoplano",
                "flight_plan": flight_plan,
                "flight_time": str(flight_time),
                "elevation": str(elevation),
                "max_prop_diameter": str(max_prop_diameter),
                "prop_blades": str(prop_blades)
            }
            # Run Setup Finder
            # Note: The run_setup_finder method prints to stdout, which might interfere with rich progress
            # Ideally we capture it, but for now we let it mix or run fast.
            # We run it outside the progress context if we want to stream its logs, 
            # or we accept that it might be silent.
            # Actually, `automation.py` uses simple print(). Let's just run it.
            
            # Extract a larger pool if filtering is active, otherwise at least 'limit'
            # If we want detailed filtering, we likely want to scrape MORE results to find the diamonds
            extraction_limit = max(1000, limit * 5) if (manuf_filter_str.lower() != "all" or target_diam_filter) else max(50, limit)
            setup_results = auto.run_setup_finder(inputs, limit=extraction_limit)
            
            # FILTER RESULTS
            if manuf_filter_str.lower() != "all" or target_diam_filter:
                # Use the fast filtering algorithm
                filtered = []
                
                # Retrieve manufacturers as list
                m_list = [m.strip() for m in manuf_filter_str.split(",") if m.strip()]
                if not m_list and manuf_filter_str.lower() != "all":
                     m_list = [manuf_filter_str] # fallback
                
                # Apply filter for each manufacturer (OR logic for manufacturers)
                # But filter_setups takes ONE manufacturer string. We can iterate.
                
                if not m_list: # No manuf filter, just diameter
                     filtered = auto.filter_setups(setup_results, target_diam_filter if target_diam_filter else -1, "")
                else:
                    for m in m_list:
                        # If diameter is None, pass -1 or similar to ignore it in filter_setups?
                        # I need to update filter_setups to handle optional diameter?
                        # Actually filter_setups implementation I wrote checks:
                        # if abs(d_val - target_diam) < 0.1:
                        # So if target_diam is passed as -1, it checks abs...
                        
                        # Let's refine the logic:
                        # We used auto.filter_setups(setups, target_diam, manufacturer)
                        # The implementation does AND logic (Diam AND Manuf).
                        pass
                        
                    # Let's do a custom loop here to be safe leveraging the method or just inline logic?
                    # The user explicitly asked for "find and make a fast algorithm".
                    # I should use the one in automation.py or refine it.
                    
                    # Let's use it. We can handle the "All" case.
                    # Actually, let's keep it simple here.
                    
                    for s in setup_results:
                        # Manuf Check
                        pass_manuf = False
                        if manuf_filter_str.lower() == "all":
                            pass_manuf = True
                        else:
                            s_manuf = auto._normalize_text(s.get("manufacturer", ""))
                            s_motor = auto._normalize_text(s.get("motor_name", ""))
                            for m in m_list:
                                m_norm = auto._normalize_text(m)
                                if m_norm in s_manuf or m_norm in s_motor:
                                    pass_manuf = True
                                    break
                        
                        # Diam Check
                        pass_diam = False
                        if not target_diam_filter:
                            pass_diam = True
                        else:
                            raw_diam = s.get("prop_diam", "")
                            try:
                                d_val = auto._parse_prop_diameter(raw_diam)
                                if auto._matches_prop_diameter(d_val, target_diam_filter):
                                    pass_diam = True
                            except: pass
                            
                        if pass_manuf and pass_diam:
                            filtered.append(s)

                setup_results = filtered
                progress.console.print(f"[dim]Filtered results to {len(setup_results)} setups based on filters.[/dim]")
            
            progress.update(task, description=f"Found {len(setup_results)} setups. Processing Top {limit} in PropCalc...")
            
            final_results = []
            top_setups = setup_results[:limit]
            
            # Save Run Data (Inputs + Setups)
            run_data = {
                "configuration": {
                    "weight": weight,
                    "wingspan": wingspan,
                    "wing_area": wing_area,
                    "speed": speed,
                    "thrust": thrust,
                    "max_motor_weight_pct": max_motor_weight_pct,
                    "analyzed_power": analyzed_power,
                    "battery_cells": battery_cells,
                    "battery_charge_state": battery_charge_state,
                    "esc_model": esc_model,
                    "battery_model": battery_model,
                    "flight_plan": flight_plan,
                    "flight_time": flight_time,
                    "elevation": elevation,
                    "max_prop_diameter": max_prop_diameter,
                    "prop_blades": prop_blades,
                    "prop_type": prop_type
                },
                "setups_to_analyze": top_setups
            }
            
            try:
                output_dir = get_output_dir()
                with open(os.path.join(output_dir, "last_run_data.json"), "w", encoding="utf-8") as f:
                    json.dump(run_data, f, indent=4, ensure_ascii=False)
                console.print(f"[dim]Saved run data to '{output_dir}\\last_run_data.json'[/dim]")
            except Exception as e:
                console.print(f"[red]Failed to save run data: {e}[/red]")
            
            for i, setup in enumerate(top_setups):
                motor_name = setup.get("motor_name", "Unknown")
                setup["esc"] = esc_model
                setup["battery_model"] = battery_model
                setup["weight"] = weight
                setup["analyzed_power"] = analyzed_power
                setup["battery_cells"] = battery_cells
                setup["battery_charge_state"] = battery_charge_state
                setup["prop_type"] = prop_type
                progress.update(task, description=f"Analyzing Motor {i+1}/{len(top_setups)}: [cyan]{motor_name}[/cyan]")
                
                pc_res = auto.run_prop_calc(setup)
                
                # Merge ALL results from PropCalc into a single dictionary
                combined = {
                    "motor": motor_name,
                    "kv": setup.get("motor_kv", "?"),
                    "manufacturer": setup.get("manufacturer", ""),
                    "prop": f"{setup.get('prop_diam', '?')}x{setup.get('prop_pitch', '?')}",
                    **pc_res # Spread all keys from pc_res (power, traction_v, effs, motor_weight etc)
                }
                final_results.append(combined)

        # Display Results
        console.print("\n[bold yellow]STEP 3: Results[/bold yellow]")
        
        from rich import box
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE_HEAD)
        table.add_column("Marca", no_wrap=True)
        table.add_column("Motor", no_wrap=True)
        table.add_column("Helice", no_wrap=True)
        table.add_column("Passo", no_wrap=True)
        table.add_column("Massa (g)")
        table.add_column("Pwr (W)", style="bold cyan")
        table.add_column("Eff Max(%)", style="bold yellow")
        table.add_column("Eff Pwr(%)", style="bold yellow")
        table.add_column("Thrst @Pwr(g)", style="dim")
        table.add_column("Trac(0kmh)", style="bold green")
        
        console.print(f"[dim]Debug: Preparing table for {len(final_results)} motors...[/dim]")
        for res in final_results:
            # Debug log to verify data presence
            # console.print(f"[dim]Data for {res.get('motor')}: Power={res.get('power')}, Weight={res.get('motor_weight')}[/dim]")
            
            row = [
                res.get("manufacturer", ""),
                res.get("motor", "Unknown"),
                str(res.get("prop_diam", "?")),
                str(res.get("prop_pitch", "?")),
                res.get("drive_weight", res.get("motor_weight", "N/A")),
                res.get("power", "N/A"),
                res.get("eff_max_throttle", "N/A"),
                res.get("eff_at_power", "N/A"),
                res.get("thrust_at_power", "N/A"),
                res.get("traction_0", "N/A")
            ]
            table.add_row(*row)
            
        console.print(table)
        console.print("[dim]Note: Full speed sweep results (0-135km/h) are available in the CSV/Planilha.[/dim]")
        
        # Save to CSV (Planilhas)
        try:
            output_dir = get_output_dir()
            plan_dir = os.path.join(output_dir, "Planilhas")
            if not os.path.exists(plan_dir):
                os.makedirs(plan_dir)
                
            filename = os.path.join(plan_dir, f"P{analyzed_power} - N{limit}.csv")
            
            with open(filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
                
                # Dynamic Header based on User Request
                # marca, motor, preco, massa[g], link, diametro, passo, pa, Throttle100Pot[W], Throttle100tracao0[g], T100tracao9...
                
                header = [
                    "marca", "motor", "preco", "massa[g]", "link", 
                    "diametro", "passo", "pa", 
                    "Throttle100Pot[W]", "Throttle100tracao0[g]"
                ]
                
                # Dynamic Speed Columns (T100tracao{v}) - skipping 0 as it is already above
                speeds = list(range(9, 136, 9)) 
                for v in speeds:
                    header.append(f"T100tracao{v}")
                    
                header.append("Throttle100Ef[%]")
                
                # Approx Power Columns
                p_label = f"Pot≈{analyzed_power}"
                header.extend([
                    f"{p_label}Throttle[%]",
                    f"{p_label}Pot[W]",
                    f"{p_label}Ef[%]",
                    f"{p_label}Tracao[g]"
                ])
                    
                writer.writerow(header)
                
                # Rows
                for res in final_results:
                    # Use Drive Weight for "massa[g]" as requested
                    weight_val = res.get("drive_weight", "N/A")
                    if weight_val == "N/A":
                         weight_val = res.get("motor_weight", "N/A")

                    row = [
                        res.get("manufacturer", ""),
                        res.get("motor", "Unknown"),
                        "", # preco
                        weight_val, # massa[g]
                        "", # link
                        str(res.get("prop_diam", "?")),
                        str(res.get("prop_pitch", "?")),
                        str(res.get("prop_blades", "2")), # pa
                        res.get("power", "N/A"), # Throttle100Pot[W]
                        res.get("traction_0", "N/A"), # Throttle100tracao0[g]
                    ]
                    
                    # Speed columns
                    for v in speeds:
                        row.append(res.get(f"traction_{v}", "N/A"))
                        
                    row.append(res.get("eff_max_throttle", "N/A")) # Throttle100Ef[%]
                    
                    # Analyzed Power columns
                    row.append(res.get("thr_at_power", "N/A"))
                    row.append(res.get("power_at_eff", "N/A"))
                    row.append(res.get("eff_at_power", "N/A"))
                    row.append(res.get("thrust_at_power", "N/A"))
                    
                    writer.writerow(row)
                    
            console.print(f"\n[bold green]Results saved to spreadsheet:[/bold green] {filename}")
            
        except Exception as ex:
             console.print(f"[red]Failed to save spreadsheet: {ex}[/red]")
        
    except Exception as e:
        console.print(f"[bold red]An error occurred:[/bold red] {e}")
    finally:
        if 'close_browser' in locals() and close_browser == 'n':
            console.print("\n[bold yellow]Browser is open. Press Enter to close and exit...[/bold yellow]")
            input()
        
        console.print("\n[dim]Closing browser...[/dim]")
        auto.stop()

if __name__ == "__main__":
    main()
