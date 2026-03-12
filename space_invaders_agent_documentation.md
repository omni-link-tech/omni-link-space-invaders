# Space Invaders Master Agent Documentation

## Overview

This document describes the **Space Invaders Master** demo built for the
Omni Link platform.  Space Invaders is a fixed‑shooter game where the
player’s ship battles waves of descending aliens.  In this demo the
ship at the bottom of the screen is controlled by the Omni Link agent.
The demo shows how the agent can receive live game data via WebSockets,
move the ship left or right, fire bullets and achieve high scores.

The Space Invaders Master agent’s responsibilities include:

* Greeting the user and offering to play or discuss Space Invaders.
* Explaining the rules and strategy of the game.
* Directing the user to run the **space_invaders.html** file and start
  the relay server for real‑time feedback.
* Controlling the ship by sending movement and firing commands over
  WebSockets or activating the built‑in AI.

## Game Implementation and WebSocket Integration

The game is contained in `space_invaders.html`, a single HTML/JavaScript
file.  It renders the playfield and updates game logic at roughly 60 fps.
Key features are:

* **Ship and bullet** – The player’s ship moves horizontally along the
  bottom of the screen and can shoot bullets upward.  Only one bullet
  can be on screen at a time; if it hits an alien or leaves the screen
  it disappears.
* **Alien formation** – Aliens are arranged in a grid.  They move
  horizontally and descend one row each time they hit the screen edge.
  If the aliens reach the bottom, the wave resets.  Destroying all
  aliens spawns a new wave, allowing continuous play.
* **Agent control functions** – The ship can be moved using
  `moveAgentShip(direction)` (direction is `left`, `right` or `stop`).
  The `shoot()` function fires a bullet if none is present.  These
  functions are called internally when receiving commands from the
  WebSocket or when the built‑in AI (`startAgentAI()`) is activated.
* **WebSocket state** – Each frame, the game sends a JSON object
  containing the ship position, bullet position, a list of alive aliens
  (as centre coordinates), number of remaining aliens and the current
  score to `ws://localhost:6789/game_invaders`.  It listens for
  `action` messages with `move` and an optional `shoot` flag, or for
  `ai` messages to start the internal AI.

### Relay Server

The relay server (`space_invaders_ws_server.py`) acts as a
communication bridge between the game and the agent.  Clients connect
to `/game_invaders` (for the game) or `/agent_invaders` (for the agent).
Messages are forwarded unchanged between the two clients, allowing the
agent to see live game data and send commands.

### Reference Agent

The sample agent (`space_invaders_agent.py`) demonstrates how to use
the WebSocket interface.  It connects to the agent endpoint, reads the
list of alive aliens from the game state and moves toward the lowest
alien in the formation.  When the ship is aligned with the target and
no bullet is on screen, it fires.  This strategy achieves a high hit
rate and clears waves efficiently.

## Knowledge File

The file **`space_invaders_knowledge.md`** summarises the rules,
strategies and the demo AI behaviour for Space Invaders.  Upload this
file to the **Knowledge** section of Omni Link to give the agent the
context needed to answer questions about the game.

## Agent Configuration

To set up a Space Invaders agent in Omni Link, configure the following
elements in the **Configuration** panel:

* **Main Task** – Describe the agent as a master Space Invaders pilot
  capable of explaining rules, giving strategy tips and demonstrating
  expert play via WebSockets.  Instruct the agent to guide the user
  through starting the relay server and game.
* **Available Commands** – Suggested commands:
  * `greet`: Introduces the agent and its abilities.
  * `describe_space_invaders_rules`: Outlines player controls, alien
    movement and scoring.
  * `describe_space_invaders_strategy`: Provides tips such as focusing
    on one column and anticipating alien movement.
  * `start_space_invaders_game`: Advises running
    `space_invaders_ws_server.py` and opening `space_invaders.html`, and
    describes what the user will see.
  * `start_space_invaders_ai`: Provides a JavaScript snippet to call
    `startAgentAI()` or instructs the user to run the reference agent
    for a WebSocket demonstration.
* **Agent Name** – e.g. **“Space Invaders Master”**.
* **Agent Personality** – Confident, encouraging and tactical, emphasising
  precision and timing.
* **Custom Instructions** – Remind the agent to report the current
  score, mention remaining aliens, and maintain friendly, concise
  responses.
* **Code Responses & Tool Usage** – Enable both.

Saving these settings and uploading the knowledge file prepares the
agent for interactions.

## Testing & Results

During testing, the Space Invaders Master agent performed as follows:

1. **Greeting** – It welcomed the user and explained it could discuss
   the game or start a demonstration.
2. **Rules and strategy** – It clearly described the controls, alien
   patterns and key tactics for success.
3. **Game startup** – When prompted to start a game, it instructed
   running the relay server and opening `space_invaders.html`, noting
   that the ship would remain stationary until commands were sent or
   the built‑in AI was activated.
4. **AI demonstration** – Running the relay server and reference
   agent produced a ship that moved under the lowest alien and fired
   accurately.  The aliens were defeated without reaching the bottom
   of the screen.  The agent reported the live score and commented
   on the number of remaining aliens as the game progressed.

## Conclusion & Future Work

The Space Invaders Master demo shows how Omni Link can power a classic
arcade shooter with real‑time agent control.  By broadcasting the game
state over WebSockets and exposing simple control functions, the agent
can play effectively or coach the user.  Future enhancements could
include multiple bullet shots, alien projectiles to dodge, variable
alien speeds, and personal high‑score tracking.  As it stands, the
demo successfully demonstrates mastery of the mechanics and a
compelling integration with Omni Link.