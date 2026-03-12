## Space Invaders Knowledge

### Game Rules

Space Invaders is a fixed‑shooter arcade game in which the player controls a
cannon (a small ship) that moves horizontally across the bottom of the
screen.  Waves of aliens march across and down the screen, periodically
firing projectiles.  The basic rules are:

1. **Player movement and firing** – The player can move the ship left or
   right and can shoot projectiles upward.  Only one projectile may be
   on screen at a time in the classic game.  In this demo the bullet
   disappears if it hits an alien or leaves the screen.
2. **Alien formation** – Aliens are arranged in a grid.  They move
   horizontally as a group, reversing direction and descending one row
   each time they hit a wall.  If any alien reaches the bottom of the
   playfield, the game resets (or in the original game, the player
   loses).
3. **Scoring** – Destroying an alien awards points.  In the original
   game, different alien types award different points; in this demo all
   aliens award 10 points.
4. **Winning** – The objective is to eliminate all aliens before they
   descend too far.  Once a wave is cleared, a new wave appears and the
   game continues indefinitely.

### Strategy and Tactics

Key strategies for Space Invaders include:

* **Focus on one column** – Clearing an entire column of aliens gives
  the player extra space and more time because the alien group’s width
  shrinks, delaying their descent.
* **Aim ahead of moving targets** – Because aliens move as a group,
  the player must anticipate their movement when firing.  Aligning
  under a column and shooting just ahead can maximise hits.
* **Manage rate of fire** – In versions where only one bullet may be
  on screen, firing too early can leave the player unable to react to
  descending aliens.  It is often better to wait until a shot is
  likely to hit.
* **Watch for descent** – As the aliens get closer, their horizontal
  movement speeds up.  Adjust position quickly and focus on clearing
  the lowest rows first.

### Demo AI Overview

The Space Invaders demo includes a built‑in AI for the ship that aligns
the ship under the nearest alien and fires when aligned.  The AI scans
the list of alive aliens, targets the one closest to the bottom of the
screen, and moves the ship toward it.  Once aligned (within a small
margin), it shoots.  Because the aliens move slowly in this simplified
version, this strategy is effective for clearing waves.

### WebSocket Integration

To enable your Omni Link agent to control the ship and observe the
game’s progress in real time, the demo uses a WebSocket interface:

* The game connects to `ws://localhost:6789/game_invaders` and sends a
  JSON message each frame containing the ship’s x‑coordinate, ship
  width, bullet position (if any), a list of alive aliens’ centre
  coordinates, the number of remaining aliens and the current score.
* A relay server (`space_invaders_ws_server.py`) forwards messages
  between the game and an agent connected to
  `ws://localhost:6789/agent_invaders`.
* A reference agent (`space_invaders_agent.py`) reads the aliens list
  from the state, moves toward the lowest alien in the formation, and
  fires when aligned and no bullet is on screen.  It sends action
  messages with `move` (left, right or stop) and an optional `shoot`
  flag.

By uploading this knowledge file and configuring the agent with
appropriate commands, the Omni Link agent can explain the rules and
strategies of Space Invaders, guide the user through starting the demo,
and even control the ship either manually or via the built‑in AI using
the WebSocket interface.