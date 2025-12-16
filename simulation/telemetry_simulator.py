import asyncio
import random
from datetime import datetime
import json
import websockets
import platform

NUM_VEHICLES = 10
DTC_CODES = ["P0300", "P0171", "P0420", "P0442", "P0128", "P0455"]
USAGE_PATTERNS = ["city", "highway", "mixed"]

class Vehicle:
    def __init__(self, vehicle_id):
        self.vehicle_id = vehicle_id
        self.usage_pattern = random.choice(USAGE_PATTERNS)

    def generate_telemetry(self):
        return {
            "vehicle_id": self.vehicle_id,
            "timestamp": datetime.utcnow().isoformat(),
            "usage_pattern": self.usage_pattern,
            "engine_temp": round(random.uniform(75, 110), 2),
            "battery_voltage": round(random.uniform(11.5, 14.8), 2),
            "brake_wear": round(random.uniform(0, 80), 2),
            "tire_pressure": round(random.uniform(28, 36), 2),
            "dtc": random.choice(DTC_CODES) if random.random() < 0.1 else None
        }

vehicles = [Vehicle(f"VEH-{i+1:03d}") for i in range(NUM_VEHICLES)]

async def telemetry_handler(websocket):  # Only websocket, NO path
    print(f"Client connected: {websocket.remote_address}")
    try:
        while True:
            for vehicle in vehicles:
                await websocket.send(json.dumps(vehicle.generate_telemetry()))
            await asyncio.sleep(5)
    except websockets.ConnectionClosedOK:
        print(f"Client disconnected: {websocket.remote_address}")
    except Exception as e:
        print(f"Error in telemetry_handler: {e}")


async def main():
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    print("Starting telemetry simulator for 10 vehicles...")
    async with websockets.serve(telemetry_handler, "localhost", 8765):
        print("Telemetry WebSocket server running on ws://localhost:8765")
        await asyncio.Future()  # Keep server running


if __name__ == "__main__":
    asyncio.run(main())