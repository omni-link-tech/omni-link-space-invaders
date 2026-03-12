"""
Space Invaders agent WebSocket client

This script connects to the Space Invaders WebSocket relay server at
ws://localhost:6790/agent_invaders.  It listens for state messages from
the game and decides how to move the ship and when to shoot.  The agent
aligns the ship under the closest remaining alien and fires when aligned.

Usage:

    python space_invaders_agent.py

Ensure that the Space Invaders relay server (`space_invaders_ws_server.py`) is
running and that the game is connected to `/game_invaders`.
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
                ship_x = data["shipX"]
                ship_width = data.get("shipWidth", 40)
                ship_center = ship_x + ship_width / 2
                bullet = data.get("bullet")
                aliens = data.get("aliens", [])
                # Determine the alien closest in vertical distance (lowest y) then horizontal difference
                target = None
                # Sort aliens by y (descending) so we focus on aliens closest to ship, then by closeness in x
                if aliens:
                    # Find alien with minimal y (max y) means nearest row to bottom
                    target = min(aliens, key=lambda a: (-a["y"], abs(a["x"] - ship_center)))
                move = "stop"
                shoot = False
                tolerance = 6
                if target:
                    if ship_center < target["x"] - tolerance:
                        move = "right"
                    elif ship_center > target["x"] + tolerance:
                        move = "left"
                    else:
                        move = "stop"
                        # aligned; shoot if no bullet
                        if bullet is None:
                            shoot = True
                else:
                    # No aliens; stop and don't shoot
                    move = "stop"
                action = {"type": "action", "move": move}
                if shoot:
                    action["shoot"] = True
                await ws.send(json.dumps(action))
        except websockets.ConnectionClosed:
            print("Disconnected from Space Invaders server")


if __name__ == "__main__":
    asyncio.run(run_invaders_agent())