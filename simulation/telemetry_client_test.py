import asyncio
import websockets
import json

async def client():
    uri = "ws://localhost:8765"
    try:
        async with websockets.connect(uri) as ws:
            while True:
                data = await ws.recv()
                print(json.loads(data))
    except Exception as e:
        print(f"Client error: {e}")

if __name__ == "__main__":
    asyncio.run(client())
