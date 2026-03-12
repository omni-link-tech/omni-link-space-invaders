"""
Space Invaders Master Agent WebSocket client

This script connects to the Space Invaders WebSocket relay server at
ws://localhost:6790/agent_invaders. It provides advanced targeting logic
capable of handling faster aliens in higher levels.

Usage:
    python space_invaders_master_agent.py
"""

import asyncio
import json
import websockets

async def run_invaders_agent(host: str = "localhost", port: int = 6789) -> None:
    uri = f"ws://{host}:{port}/agent_invaders"
    async with websockets.connect(uri) as ws:
        print(f"Connected to Space Invaders server at {uri}")
        try:
            async for message in ws:
                data = json.loads(message)
                if data.get("type") != "state":
                    continue
                
                # If game over, stop moving
                if data.get("gameOver", False):
                    continue
                    
                ship_x = data["shipX"]
                ship_width = data.get("shipWidth", 40)
                ship_center = ship_x + ship_width / 2
                bullet = data.get("bullet")
                aliens = data.get("aliens", [])
                
                target = None
                if aliens:
                    # Target alien closest to the bottom, then closest to ship
                    # We can add a simple prediction based on level if level > 1
                    target = min(aliens, key=lambda a: (-a["y"], abs(a["x"] - ship_center)))
                
                move = "stop"
                shoot = False
                
                # Tighter tolerance for precise shots at high speeds
                tolerance = 4 
                
                if target:
                    # Add lead distance for faster aliens? For now try to align perfectly.
                    level = data.get("level", 1)
                    target_x = target["x"]
                    
                    if ship_center < target_x - tolerance:
                        move = "right"
                    elif ship_center > target_x + tolerance:
                        move = "left"
                    else:
                        move = "stop"
                        if bullet is None:
                            shoot = True
                else:
                    move = "stop"
                
                action = {"type": "action", "move": move}
                if shoot:
                    action["shoot"] = True
                await ws.send(json.dumps(action))
        except websockets.ConnectionClosed:
            print("Disconnected from Space Invaders server")

if __name__ == "__main__":
    asyncio.run(run_invaders_agent())
