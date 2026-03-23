# OmniLink Space Invaders Demo

A Pygame Space Invaders game controlled by a local AI engine, orchestrated through
the OmniLink platform via **tool calling**.  The AI agent never sees the game —
it simply calls the `make_move` tool, which runs a local controller that
tracks alien movement, computes lead shots, and fires with precision.

This keeps API credit usage to a minimum (one call to kick off the game).

This demo showcases four core OmniLink features:

| Feature | How it is used |
|---|---|
| **Tool Calling** | Agent calls `make_move` — the platform forwards execution to the local AI controller |
| **Commands** | Agent outputs `Command: stop_game` to end the game early |
| **Short-Term Memory** | Game state (score, lives, level, aliens) is saved periodically so the agent can answer questions |
| **Chat API** | The agent can be asked about the game state at any time from the OmniLink UI |

---

## Benchmark Results

| Metric | Value |
|---|---|
| **Final Score** | 5,420 |
| **Levels Cleared** | 8 (reached Level 9) |
| **Lives Used** | 5/5 |
| **Play Time** | 7m 9s |
| **API Calls** | 1 kick-off + ~14 reviews (1 per 30s) |
| **AI Strategy** | Lead-shot targeting with swarm direction tracking |

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.9 or later |
| OmniKey | Sign up at https://www.omnilink-agents.com |

Python packages:

```
pip install pygame requests
```

The OmniLink Python client (`omnilink-lib`) must be available on your
`PYTHONPATH`.  The script auto-adds `../../omnilink-lib/src` to `sys.path`,
so the default repo layout works out of the box.

---

## Quick Start

You need **two terminals**.

### Step 1 — Start the game server (Terminal 1)

```bash
cd omnilink-space-invaders
python server_wrapper.py
```

This launches:
- The **Pygame window** (640x600) — the Space Invaders game itself
- An **HTTP API** on **http://localhost:5003** for state polling and action sending

### Step 2 — Add your OmniKey

Open `space_invaders_link/play_space_invaders.py` and replace the `OMNI_KEY`
value with your own key:

```python
OMNI_KEY = "olink_YOUR_KEY_HERE"
```

### Step 3 — Run the AI agent (Terminal 2)

```bash
cd space_invaders_link
python -u play_space_invaders.py
```

### Step 4 — Watch and interact

- **Pygame window** — Watch the AI move the ship, aim, and fire.
- **Terminal output** — See score updates, level changes, and life events.
- **OmniLink UI** — Chat with the `space-invaders-agent` profile.
- **Stop the game** — Type *"stop the game"* in the OmniLink UI.

---

## Configuration

All settings are at the top of `space_invaders_link/play_space_invaders.py`:

```python
BASE_URL      = "https://www.omnilink-agents.com"
OMNI_KEY      = "olink_..."
AGENT_NAME    = "space-invaders-agent"
ENGINE        = "g2-engine"
POLL_INTERVAL = 0.0        # No delay — max speed
MEMORY_EVERY  = 10         # Save state to memory every N seconds
ASK_EVERY     = 30         # Agent reviews the game every N seconds
```

### Available Engines

| Engine | Model |
|---|---|
| `g1-engine` | Gemini |
| `g2-engine` | GPT-5 |
| `g3-engine` | Grok |
| `g4-engine` | Claude |

---

## How It Works

### Architecture

```
+---------------------+       +--------------------+       +------------------+
|   OmniLink Cloud    |       |  server_wrapper.py |       |   Pygame Window  |
|   Chat + Memory +   |       |  localhost:5003    |       |   640x600        |
|   Tool Calling      |       |  HTTP API + Game   |       |   Space Invaders |
+---------------------+       +--------------------+       +------------------+
        ^                            ^       |
        |  REST API                  |       | Pygame renders
        v                           |  HTTP  | directly
+---------------------+             |       |
|  play_space_invaders |-------------+       |
|  + si_engine.py      |  GET /data (poll state)
|  + si_api.py         |  POST /callback (send actions)
|  + OmniLinkClient    |
+---------------------+
```

### AI Strategy (Lead-Shot Targeting)

The engine uses a stateful approach that tracks alien movement across frames:

1. **Direction Tracking**: Compares swarm centroid positions frame-to-frame
   to determine exact swarm movement direction (left or right).

2. **Target Selection**: Scores every alien based on:
   - **Threat** (70%): Lower aliens = higher threat = priority target
   - **Ease** (30%): How quickly the ship can align and fire

3. **Lead Calculation**: Predicts where the target alien will be when the
   bullet arrives, accounting for:
   - Alien speed (increases per level: `40 + (level-1)*15` px/sec)
   - Bullet travel time (`dy / 480` px/sec)
   - Wall bounce reflections

4. **Fire Control**: Shoots when within 5px of aim point — tight tolerance
   for precision kills. Supports compound actions (LEFT_SHOOT, RIGHT_SHOOT).

### Control Loop

```
1. Kick off           One API call: agent calls Tool: make_move
2. Poll state         GET /data: ship position, aliens, bullet, score
3. Track direction    Compare alien centroid to previous frame
4. Select target      Score aliens by threat + ease, pick best
5. Lead & aim         Predict alien position at bullet arrival time
6. Fire & move        Send compound action (e.g. LEFT_SHOOT)
7. Memory sync        Save state to OmniLink every 10 seconds
8. Agent review       Every 30s: make_move to continue, stop_game to end
9. Repeat             Back to step 2
```

---

## Key Files

| File | Description |
|---|---|
| `space_invaders_link/play_space_invaders.py` | Main script — OmniLink integration, control loop, memory sync |
| `space_invaders_link/space_invaders_engine.py` | AI controller — lead-shot targeting, direction tracking |
| `space_invaders_link/space_invaders_api.py` | HTTP client for polling state and sending actions |
| `space_invaders.py` | Pygame game engine — alien formation, physics, rendering |
| `server_wrapper.py` | HTTP + MQTT bridge wrapping the Pygame game |

---

## Game Mechanics

| Parameter | Value |
|---|---|
| Window size | 640 x 600 pixels |
| Ship | 44px wide, speed 420 px/sec |
| Bullet | Speed 480 px/sec, 1 on screen at a time |
| Aliens | 5 rows x 10 columns per wave |
| Lives | 5 |
| Alien speed | 40 + (level-1) x 15 px/sec |
| Scoring | +10 per alien |

---

## Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| `429: Monthly usage limit exceeded` | OmniKey credits exhausted | Wait for monthly reset or upgrade plan |
| `Connection refused` on port 5003 | Game server not running | Start `python server_wrapper.py` first |
| No output from agent | Buffered stdout | Use `python -u` (unbuffered) |
| `ModuleNotFoundError: omnilink` | Python can't find the library | Ensure `omnilink-lib/src` is on your `PYTHONPATH` |
