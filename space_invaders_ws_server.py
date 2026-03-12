"""
WebSocket relay server for the Space Invaders demo.

This server listens on localhost:6790 and allows two types of clients to connect:

* The **game** client connects at path `/game_invaders`.  It should send state
  updates containing the ship’s position, bullet position, remaining aliens
  and score.  Messages from the game will be forwarded to the connected agent
  client (if present).

* The **agent** client connects at path `/agent_invaders`.  It should send
  action messages instructing the game to move the ship left, right or stop,
  shoot a bullet, or activate the built‑in AI.  Messages from the agent will
  be forwarded to the connected game client.

Message format is JSON.  The server does not inspect or modify payloads.

Run this server in a terminal before starting the game and agent scripts:

    python space_invaders_ws_server.py

The server runs indefinitely until interrupted (Ctrl+C).
"""

import asyncio
import json
from typing import Dict
import websockets
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion


class InvadersRelayServer:
    """Relay between Space Invaders game and agent WebSocket clients."""

    def __init__(self, host: str = "localhost", port: int = 6789) -> None:
        self.host = host
        self.port = port
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.last_state = None
        self.win_published = False
        self.mqtt_client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2, transport="websockets")
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message

    def on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        print("Connected to MQTT broker (olink)")
        client.subscribe("olink/commands")

    def on_mqtt_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            command = payload.get("command")
            if command in ["pause", "resume"]:
                if "game" in self.clients and hasattr(self, 'loop'):
                    action = {"type": "control", "command": command}
                    asyncio.run_coroutine_threadsafe(
                        self.clients["game"].send(json.dumps(action)),
                        self.loop
                    )
        except Exception as e:
            print("Failed to process MQTT message:", e)

    def setup_mqtt(self):
        try:
            self.mqtt_client.connect("localhost", 9001, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            print("MQTT connection failed:", e)

    async def publish_state_loop(self):
        while True:
            await asyncio.sleep(10)
            if self.last_state:
                try:
                    data = json.loads(self.last_state)
                    filtered_state = {
                        "remainingAliens": data.get("remainingAliens", 0),
                        "score": data.get("score", 0),
                        "lives": data.get("lives", 0),
                        "level": data.get("level", 1),
                        "gameOver": data.get("gameOver", False)
                    }
                    self.mqtt_client.publish("olink/context", json.dumps(filtered_state))
                except Exception as e:
                    pass

    async def handler(self, websocket) -> None:
        try:
            path = websocket.request.path
        except AttributeError:
            path = websocket.path # For older websockets versions if any
        role = None
        if path == "/game_invaders":
            role = "game"
        elif path == "/agent_invaders":
            role = "agent"
        else:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                role = data.get("role")
            except Exception:
                await websocket.close(code=4000, reason="Unknown client role")
                return
        self.clients[role] = websocket
        print(f"Invaders {role} client connected from {websocket.remote_address}")
        try:
            async for message in websocket:
                if role == "game":
                    self.last_state = message
                    
                    # Intercept win condition from backend
                    try:
                        state_data = json.loads(message)
                        if state_data.get("type") == "state" and state_data.get("level", 1) >= 5 and not self.win_published:
                            self.win_published = True
                            win_payload = json.dumps({
                                "source": "Space Invaders Game",
                                "message": "I win! Successfully reached Level 5.",
                                "score": state_data.get("score", 0)
                            })
                            print(f"[BACKEND] Win Condition Met! Publishing to MQTT: {win_payload}")
                            self.mqtt_client.publish("olink/context", win_payload)
                    except Exception as e:
                        print("Error checking win condition:", e)
                        
                    if "agent" in self.clients:
                        await self.clients["agent"].send(message)
                elif role == "agent" and "game" in self.clients:
                    await self.clients["game"].send(message)
        except websockets.ConnectionClosed:
            pass
        finally:
            if self.clients.get(role) is websocket:
                del self.clients[role]
            print(f"Invaders {role} client disconnected from {websocket.remote_address}")

    async def run(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.setup_mqtt()
        asyncio.create_task(self.publish_state_loop())
        async with websockets.serve(self.handler, self.host, self.port):
            print(f"Space Invaders relay server running on ws://{self.host}:{self.port}")
            await asyncio.Future()


if __name__ == "__main__":
    server = InvadersRelayServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("Server stopped")