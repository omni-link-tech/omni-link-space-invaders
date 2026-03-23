"""Local Space Invaders AI engine — unbeatable targeting and ship control.

Stateful engine that tracks alien movement across frames to compute
exact lead shots.  Prioritises threat elimination while minimising
idle time between kills.
"""

from __future__ import annotations

from typing import Any

# Game constants (must match space_invaders.py).
WIDTH = 640
HEIGHT = 600
SHIP_WIDTH = 44
SHIP_Y = HEIGHT - 50       # 550
SHIP_SPEED = 420            # px/sec
BULLET_SPEED = 480          # px/sec
ALIEN_H = 22                # alien height (descent per bounce)
DEADZONE = 3                # tight pixel tolerance — precision kills
FIRE_TOLERANCE = 5          # shoot if within this many pixels of aim point


# ── Stateful direction tracker ────────────────────────────────────────

class _Tracker:
    """Tracks alien swarm direction across frames."""

    def __init__(self):
        self.prev_centroid_x: float | None = None
        self.direction: int = 1  # 1 = right, -1 = left

    def update(self, aliens: list[dict]) -> int:
        """Update direction estimate from current alien positions.

        Compares the swarm centroid to the previous frame.  This gives
        an exact direction rather than a wall-proximity guess.
        """
        if not aliens:
            return self.direction

        cx = sum(a["x"] for a in aliens) / len(aliens)

        if self.prev_centroid_x is not None:
            dx = cx - self.prev_centroid_x
            if abs(dx) > 0.1:
                self.direction = 1 if dx > 0 else -1

        self.prev_centroid_x = cx
        return self.direction


_tracker = _Tracker()


# ── Lead calculation ──────────────────────────────────────────────────

def _lead_target_x(target: dict, state: dict[str, Any], direction: int) -> float:
    """Predict where the target alien will be when the bullet arrives.

    Uses exact alien speed from level, tracked direction, and full
    bullet travel time — no dampening.
    """
    level = state.get("level", 1)
    alien_speed = 40 + (level - 1) * 15  # px/sec

    dy = SHIP_Y - target["y"]
    if dy <= 0:
        return target["x"]
    travel_time = dy / BULLET_SPEED

    predicted_x = target["x"] + direction * alien_speed * travel_time

    # If predicted position is near a wall, the aliens will bounce.
    # Reflect the prediction to stay accurate.
    aliens = state.get("aliens", [])
    if aliens:
        half_w = 16  # half alien width
        min_ax = min(a["x"] for a in aliens) - half_w
        max_ax = max(a["x"] for a in aliens) + half_w

        # How far the swarm can travel before hitting a wall
        if direction == 1:
            room = (WIDTH - 5) - max_ax
        else:
            room = min_ax - 5

        travel_dist = alien_speed * travel_time
        if travel_dist > room and room > 0:
            # Will bounce — reflect the overshoot
            overshoot = travel_dist - room
            predicted_x = target["x"] + direction * room - direction * overshoot
        # If already past wall, just use raw prediction clamped
    return max(half_w, min(WIDTH - half_w, predicted_x))


# ── Target selection ──────────────────────────────────────────────────

def _pick_target(state: dict[str, Any], direction: int) -> dict | None:
    """Select the optimal alien to kill next.

    Scoring system weighing:
    - Threat (lower aliens = higher threat = bigger score)
    - Ease (how quickly the ship can align and fire)
    - Efficiency (prefer aliens where lead shot is short travel)
    """
    aliens = state.get("aliens", [])
    if not aliens:
        return None

    ship_center = state["shipX"] + state.get("shipWidth", SHIP_WIDTH) / 2
    bullet = state.get("bullet")
    level = state.get("level", 1)
    alien_speed = 40 + (level - 1) * 15

    best = None
    best_score = float("inf")

    for a in aliens:
        # Compute where we'd need to aim for this alien
        dy = SHIP_Y - a["y"]
        if dy <= 0:
            continue
        travel_time = dy / BULLET_SPEED
        aim_x = a["x"] + direction * alien_speed * travel_time

        # Clamp
        aim_x = max(SHIP_WIDTH / 2, min(WIDTH - SHIP_WIDTH / 2, aim_x))

        # Time for ship to reach aim point
        ship_travel = abs(ship_center - aim_x) / SHIP_SPEED

        # If bullet is active, we must wait for it to clear first
        if bullet is not None:
            bullet_clear_time = bullet["y"] / BULLET_SPEED
            ship_travel = max(ship_travel, bullet_clear_time)

        # Total time = ship travel + bullet travel
        total_time = ship_travel + travel_time

        # Threat penalty: lower aliens get big bonus (lower score = better)
        # Normalise y: 0 at top, 1 at ship row
        threat = 1.0 - (a["y"] / SHIP_Y)  # 0 = at ship (max threat), 1 = at top

        # Combined score: weighted sum (lower = better target)
        # Heavy threat weight so we always kill the lowest aliens first
        # unless another alien is much easier to hit
        score = total_time * 0.3 + threat * 0.7

        if score < best_score:
            best_score = score
            best = a

    return best


# ── Action decision ──────────────────────────────────────────────────

def decide_action(state: dict[str, Any]) -> str:
    """Decide the ship action based on the current game state.

    Returns one of: ``'LEFT'``, ``'RIGHT'``, ``'STOP'``,
    ``'LEFT_SHOOT'``, ``'RIGHT_SHOOT'``, ``'STOP_SHOOT'``.
    """
    aliens = state.get("aliens", [])
    direction = _tracker.update(aliens)

    target = _pick_target(state, direction)
    if target is None:
        return "STOP"

    ship_center = state["shipX"] + state.get("shipWidth", SHIP_WIDTH) / 2
    aim_x = _lead_target_x(target, state, direction)

    bullet = state.get("bullet")
    can_shoot = bullet is None

    offset = aim_x - ship_center

    # Determine move direction with tight deadzone
    if offset > DEADZONE:
        move = "RIGHT"
    elif offset < -DEADZONE:
        move = "LEFT"
    else:
        move = "STOP"

    # Shoot as soon as we're within fire tolerance — don't wait for
    # perfect alignment.  This dramatically increases fire rate.
    if can_shoot and abs(offset) <= FIRE_TOLERANCE:
        return f"{move}_SHOOT" if move != "STOP" else "STOP_SHOOT"

    return move


# ── State summary (for OmniLink memory) ──────────────────────────────

def state_summary(state: dict[str, Any]) -> str:
    """Build a concise text summary of the current game state."""
    remaining = state.get("remainingAliens", 0)
    lives = state.get("lives", 0)
    score = state.get("score", 0)
    level = state.get("level", 1)
    game_over = state.get("gameOver", False)
    ship_x = state.get("shipX", 0)
    ship_w = state.get("shipWidth", SHIP_WIDTH)
    bullet = state.get("bullet")
    play_time = state.get("play_time", 0)

    game_state = "GAMEOVER" if game_over else state.get("game_state", "PLAY")
    bullet_info = f"({bullet['x']:.0f}, {bullet['y']:.0f})" if bullet else "None"
    minutes = int(play_time) // 60
    seconds = int(play_time) % 60

    return (
        f"Game state: {game_state}\n"
        f"Score: {score} | Level: {level} | Lives: {lives}\n"
        f"Play time: {minutes}m {seconds}s\n"
        f"Aliens remaining: {remaining}\n"
        f"Ship position: x={ship_x:.0f}, width={ship_w}\n"
        f"Active bullet: {bullet_info}"
    )
