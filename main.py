from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from automation import ECalAutomator
import time
import os
import json

app = FastAPI(title="eCalc Automation API")

def load_credentials():
    email = os.getenv("ECALC_EMAIL")
    password = os.getenv("ECALC_PASSWORD")
    if email and password:
        return {"email": email, "password": password}
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "credentials.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    raise HTTPException(status_code=500, detail="Credentials not found")

class SetupFinderInput(BaseModel):
    weight: str
    wingspan: str
    wing_area: str
    speed: str
    thrust: str
    battery_cells: str
    # Optional fields or default to common values if not provided
    wing_type: Optional[str] = "Monoplano"
    
class MotorResult(BaseModel):
    motor_name: str
    prop_diam: str
    prop_pitch: str
    power: str
    traction: str
    motor_weight: Optional[str] = "N/A"
    drive_weight: Optional[str] = "N/A"
    manufacturer: Optional[str] = ""

@app.get("/")
def read_root():
    return {"status": "eCalc Automation API is running"}

@app.post("/api/calculate", response_model=List[MotorResult])
def run_calculation(input_data: SetupFinderInput):
    print(f"Received request: {input_data}")
    # Initialize Automator
    # Note: In production, we might want a persistent browser or session
    # For now, we launch a new instance per request or use a singleton pattern carefully.
    # Spawning a browser for each request is slow but safe for state isolation.
    
    auto = ECalAutomator(headless=False) # Keep visible for demo/debug
    results = []
    
    try:
        auto.start()
        
        creds = load_credentials()
        auto.login(creds["email"], creds["password"])
        
        # Prepare inputs
        inputs = {
            "weight": input_data.weight,
            "wingspan": input_data.wingspan,
            "wing_area": input_data.wing_area,
            "speed": input_data.speed,
            "thrust": input_data.thrust,
            "battery_cells": input_data.battery_cells,
            "wing_type": input_data.wing_type
        }
        
        # 1. Setup Finder
        setup_results = auto.run_setup_finder(inputs)
        
        # Limit to top 10
        top_setups = setup_results[:10]
        
        # 2. Prop Calc Loop
        final_results = []
        for setup in top_setups:
            pc_res = auto.run_prop_calc(setup)
            
            # Combine data
            combined = {
                "motor_name": setup.get("motor_name", "Unknown"),
                "prop_diam": setup.get("prop_diam", "?"),
                "prop_pitch": setup.get("prop_pitch", "?"),
                "manufacturer": setup.get("manufacturer", ""),
                "power": pc_res.get("power", "N/A"),
                "traction": pc_res.get("traction", "N/A"),
                "motor_weight": pc_res.get("motor_weight", "N/A"),
                "drive_weight": pc_res.get("drive_weight", "N/A")
            }
            final_results.append(combined)
            
        return final_results
        
    except Exception as e:
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        auto.stop()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
