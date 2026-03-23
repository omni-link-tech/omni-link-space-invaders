"""HTTP server wrapper for the Space Invaders Pygame game.

Wraps the Pygame game with an HTTP REST API so the OmniLink agent link
can poll state and send actions — identical architecture to the Breakout
server wrapper.

Endpoints
---------
GET  /data      → current game state (JSON)
POST /callback  → accept actions (move + shoot)

Usage
-----
    python -u server_wrapper.py
"""

import sys
import re
import threading
import time
import json

import pygame
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import paho.mqtt.client as mqtt

from space_invaders import SpaceInvaders

# ── Configuration ─────────────────────────────────────────────────────
HTTP_PORT     = 5003
MQTT_BROKER   = "localhost"
MQTT_PORT     = 1883
CMD_TOPIC     = "olink/commands"
CTX_TOPIC     = "olink/context"
PUBLISH_EVERY = 20

# ── Shared state ──────────────────────────────────────────────────────
_GAME: SpaceInvaders = None
_VERSION = 0


# ──────────────────────────────────────────────────────────────────────
# State builder
# ──────────────────────────────────────────────────────────────────────
def _build_state(game: SpaceInvaders) -> dict:
    alive_aliens = []
    for a in game.aliens:
        if a["alive"]:
            r = a["rect"]
            alive_aliens.append({"x": r.centerx, "y": r.centery})

    return {
        "type":            "state",
        "shipX":           game.ship_x,
        "shipWidth":       44,  # SHIP_WIDTH
        "bullet":          game.bullet,  # dict with x,y or None
        "aliens":          alive_aliens,
        "remainingAliens": len(alive_aliens),
        "score":           game.score,
        "lives":           game.lives,
        "level":           game.level,
        "play_time":       game.play_time,
        "game_state":      game.state,
        "gameOver":        game.state == "GAMEOVER",
        "width":           640,
        "height":          600,
    }


# ──────────────────────────────────────────────────────────────────────
# Pause / resume parser
# ──────────────────────────────────────────────────────────────────────
def _parse_cmd(raw: str):
    raw = raw.strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            for key in ("command", "action", "cmd"):
                if key in data:
                    return str(data[key])
        if isinstance(data, str):
            return data
    except json.JSONDecodeError:
        pass
    m = re.search(r'["\']?(?:command|action|cmd)["\']?\s*:\s*["\']?(\w+)["\']?', raw, re.I)
    if m:
        return m.group(1)
    if raw.lower() in ("pause", "resume", "pause_game", "resume_game"):
        return raw
    return None


def _apply_cmd(cmd: str):
    game = _GAME
    if game is None:
        return
    cmd_l = cmd.strip().lower().strip("\"'")
    if cmd_l in ("pause", "pause_game"):
        if game.state == "PLAY":
            game.toggle_pause()
            print(f"[MQTT] PAUSED  (cmd='{cmd}')")
    elif cmd_l in ("resume", "resume_game"):
        if game.state == "PAUSE":
            game.toggle_pause()
            print(f"[MQTT] RESUMED  (cmd='{cmd}')")
    else:
        print(f"[MQTT] Unknown command: '{cmd}'")


# ──────────────────────────────────────────────────────────────────────
# MQTT
# ──────────────────────────────────────────────────────────────────────
def _on_connect(client, userdata, flags, rc, props=None):
    if rc == 0:
        print(f"[MQTT] Connected to {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(CMD_TOPIC)
        print(f"[MQTT] Subscribed to '{CMD_TOPIC}'")
    else:
        print(f"[MQTT] Connection failed rc={rc}")


def _on_message(client, userdata, msg):
    raw = msg.payload.decode("utf-8", errors="replace")
    print(f"[MQTT] <- '{msg.topic}': {raw}")
    cmd = _parse_cmd(raw)
    if cmd:
        _apply_cmd(cmd)


def _publisher_loop(client):
    last = time.time()
    while True:
        time.sleep(1)
        if time.time() - last >= PUBLISH_EVERY and _GAME is not None:
            last = time.time()
            g = _GAME
            payload = {
                "topic":     "space_invaders_summary",
                "score":     g.score,
                "level":     g.level,
                "lives":     g.lives,
                "state":     g.state,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            client.publish(CTX_TOPIC, json.dumps(payload))
            print(f"[MQTT] > '{CTX_TOPIC}': score={g.score} level={g.level} lives={g.lives}")


def start_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = _on_connect
    client.on_message = _on_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        print(f"[MQTT] WARNING: Cannot connect - {e}")
        return
    threading.Thread(target=_publisher_loop, args=(client,), daemon=True, name="mqtt-pub").start()


# ──────────────────────────────────────────────────────────────────────
# HTTP API
# ──────────────────────────────────────────────────────────────────────
class SpaceInvadersAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_GET(self):
        global _VERSION
        if self.path != "/data":
            self.send_error(404); return
        if _GAME is None:
            self.send_error(503, "Game not ready"); return

        _VERSION += 1
        state = _build_state(_GAME)
        payload = {
            "command": "ACTIVATE" if _GAME.state == "PLAY" else "IDLE",
            "payload": json.dumps(state),
            "version": _VERSION,
        }
        data = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors(); self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path != "/callback":
            self.send_error(404); return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8", errors="replace")
        try:
            data = json.loads(body)
            action = data.get("action")
            actions = data.get("actions")

            if isinstance(actions, list) and len(actions) > 0 and _GAME:
                for act in actions:
                    _process_action(str(act).upper())
            elif action and isinstance(action, str) and _GAME:
                _process_action(action.upper())
        except Exception as e:
            print(f"[HTTP] /callback parse error: {e}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._cors(); self.end_headers()
        self.wfile.write(b'{"status":"ok"}')


def _process_action(act: str):
    """Apply an action string to the game."""
    game = _GAME
    if game is None:
        return

    # Compound actions: LEFT_SHOOT, RIGHT_SHOOT, STOP_SHOOT
    if act in ("LEFT", "RIGHT", "STOP", "LEFT_SHOOT", "RIGHT_SHOOT",
               "STOP_SHOOT", "SHOOT"):
        game.current_action = act
    elif act in ("RESUME", "START"):
        if game.state == "PAUSE":
            game.toggle_pause()
    elif act == "PAUSE":
        if game.state == "PLAY":
            game.toggle_pause()


def run_http():
    server = ThreadingHTTPServer(("", HTTP_PORT), SpaceInvadersAPIHandler)
    print(f"[HTTP] API on port {HTTP_PORT}")
    server.serve_forever()


# ──────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    threading.Thread(target=run_http, daemon=True, name="http").start()
    start_mqtt()

    print("[Game] Initialising Space Invaders...")
    game = SpaceInvaders()
    _GAME = game

    print("[Game] Ready - waiting for agent commands on port", HTTP_PORT)
    try:
        game.run()
    except SystemExit:
        pass
    except Exception as exc:
        print(f"[Game] Crash: {exc}")
    finally:
        print("[Game] Exiting.")
        pygame.quit()
        sys.exit(0)
