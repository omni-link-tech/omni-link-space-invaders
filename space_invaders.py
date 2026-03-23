"""Space Invaders — Pygame implementation for OmniLink.

A polished, visually improved Space Invaders game that can be controlled
both by keyboard and by an external agent via the server wrapper.

Controls
--------
Arrow keys : move ship
Space      : shoot
P / Pause  : toggle pause
"""

import math
import random
import pygame

# ── Configuration ─────────────────────────────────────────────────────
WIDTH, HEIGHT = 640, 600
FPS = 60

# Colors
BLACK      = (0, 0, 0)
WHITE      = (255, 255, 255)
CYAN       = (0, 220, 255)
GREEN      = (50, 255, 80)
LIME       = (120, 255, 50)
YELLOW     = (255, 230, 40)
ORANGE     = (255, 150, 30)
RED        = (255, 50, 50)
MAGENTA    = (255, 60, 180)
DARK_BLUE  = (8, 8, 30)
GRID_DIM   = (20, 25, 50)

# Ship
SHIP_WIDTH  = 44
SHIP_HEIGHT = 18
SHIP_Y      = HEIGHT - 50
SHIP_SPEED  = 420  # pixels per second

# Bullet
BULLET_W    = 3
BULLET_H    = 12
BULLET_SPEED = 480  # pixels per second

# Aliens
ALIEN_ROWS  = 5
ALIEN_COLS  = 10
ALIEN_W     = 32
ALIEN_H     = 22
ALIEN_PAD_X = 12
ALIEN_PAD_Y = 10
ALIEN_OFFSET_X = (WIDTH - ALIEN_COLS * (ALIEN_W + ALIEN_PAD_X)) // 2
ALIEN_OFFSET_Y = 70

# Row colour scheme (top to bottom)
ROW_COLORS = [MAGENTA, RED, ORANGE, YELLOW, LIME]

# Stars
NUM_STARS = 120


class SpaceInvaders:
    """Main Space Invaders game class."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("OmniLink Space Invaders")
        self.clock = pygame.time.Clock()

        try:
            self.font_large = pygame.font.Font(
                pygame.font.match_font("courier", bold=True), 48
            )
            self.font_medium = pygame.font.Font(
                pygame.font.match_font("courier", bold=True), 28
            )
            self.font_small = pygame.font.Font(
                pygame.font.match_font("courier", bold=True), 18
            )
        except Exception:
            self.font_large = pygame.font.SysFont("monospace", 48, bold=True)
            self.font_medium = pygame.font.SysFont("monospace", 28, bold=True)
            self.font_small = pygame.font.SysFont("monospace", 18, bold=True)

        # Starfield
        self.stars = [
            (random.randint(0, WIDTH), random.randint(0, HEIGHT),
             random.uniform(0.2, 1.0), random.uniform(0.3, 1.5))
            for _ in range(NUM_STARS)
        ]

        # Particles
        self.particles: list[dict] = []

        self.reset_game()
        self.state = "PAUSE"  # Wait for controller to resume
        self.start_ticks = pygame.time.get_ticks()

        # Async action from external controller
        self.current_action = None

    # ── Setup helpers ─────────────────────────────────────────────

    def _build_aliens(self):
        """Create the alien grid for the current level."""
        self.aliens: list[dict] = []
        for row in range(ALIEN_ROWS):
            color = ROW_COLORS[row % len(ROW_COLORS)]
            for col in range(ALIEN_COLS):
                ax = ALIEN_OFFSET_X + col * (ALIEN_W + ALIEN_PAD_X)
                ay = ALIEN_OFFSET_Y + row * (ALIEN_H + ALIEN_PAD_Y)
                self.aliens.append({
                    "rect": pygame.Rect(ax, ay, ALIEN_W, ALIEN_H),
                    "color": color,
                    "alive": True,
                })
        self.alien_dir = 1  # 1 = right, -1 = left
        self.alien_speed = 40 + (self.level - 1) * 15  # pixels per second

    def reset_game(self):
        self.score = 0
        self.lives = 5
        self.level = 1
        self.play_time = 0.0
        self.start_ticks = pygame.time.get_ticks()
        self.ship_x = WIDTH / 2 - SHIP_WIDTH / 2
        self.bullet = None  # dict with x, y
        self.particles.clear()
        self._build_aliens()

    def _reset_level(self):
        """Advance to a new wave of aliens."""
        self.bullet = None
        self.particles.clear()
        self._build_aliens()

    def toggle_pause(self):
        if self.state == "PLAY":
            self.state = "PAUSE"
        elif self.state == "PAUSE":
            self.state = "PLAY"
            self.start_ticks = pygame.time.get_ticks() - int(self.play_time * 1000)

    # ── Particles ─────────────────────────────────────────────────

    def _spawn_explosion(self, x, y, color, count=12):
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(40, 160)
            self.particles.append({
                "x": x, "y": y,
                "dx": math.cos(angle) * speed,
                "dy": math.sin(angle) * speed,
                "life": random.uniform(0.3, 0.7),
                "color": color,
                "size": random.uniform(1.5, 3.5),
            })

    def _update_particles(self, dt):
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] > 0:
                p["x"] += p["dx"] * dt
                p["y"] += p["dy"] * dt
                p["dy"] += 120 * dt  # gravity
                alive.append(p)
        self.particles = alive

    # ── Game logic ────────────────────────────────────────────────

    def step(self, dt):
        # ── Non-play states ───────────────────────────────────
        if self.state != "PLAY":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        if self.state in ("TITLE", "GAMEOVER"):
                            self.reset_game()
                            self.state = "PLAY"
                            self.start_ticks = pygame.time.get_ticks()
                        else:
                            self.toggle_pause()
            self._update_particles(dt)
            return

        self.play_time = (pygame.time.get_ticks() - self.start_ticks) / 1000.0

        # ── Input ─────────────────────────────────────────────
        keys = pygame.key.get_pressed()
        action = self.current_action
        shoot_requested = False

        if action and "_SHOOT" in action:
            shoot_requested = True
            action = action.replace("_SHOOT", "")
        if action == "SHOOT":
            shoot_requested = True
            action = "STOP"
        if action == "STOP":
            self.current_action = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    shoot_requested = True
                elif event.key == pygame.K_p:
                    self.toggle_pause()
                    return

        # ── Ship movement ─────────────────────────────────────
        if keys[pygame.K_LEFT] or action == "LEFT":
            self.ship_x -= SHIP_SPEED * dt
        if keys[pygame.K_RIGHT] or action == "RIGHT":
            self.ship_x += SHIP_SPEED * dt
        self.ship_x = max(0, min(WIDTH - SHIP_WIDTH, self.ship_x))

        # ── Shooting ──────────────────────────────────────────
        if shoot_requested and self.bullet is None:
            self.bullet = {
                "x": self.ship_x + SHIP_WIDTH / 2,
                "y": SHIP_Y,
            }

        # ── Bullet movement ───────────────────────────────────
        if self.bullet:
            self.bullet["y"] -= BULLET_SPEED * dt
            if self.bullet["y"] < 0:
                self.bullet = None

        # ── Alien movement ────────────────────────────────────
        hit_edge = False
        for a in self.aliens:
            if not a["alive"]:
                continue
            if self.alien_dir == 1 and a["rect"].right + self.alien_speed * dt > WIDTH - 5:
                hit_edge = True
                break
            if self.alien_dir == -1 and a["rect"].left - self.alien_speed * dt < 5:
                hit_edge = True
                break

        if hit_edge:
            self.alien_dir *= -1
            for a in self.aliens:
                a["rect"].y += ALIEN_H

        for a in self.aliens:
            if a["alive"]:
                a["rect"].x += self.alien_dir * self.alien_speed * dt

        # ── Bullet-alien collision ────────────────────────────
        if self.bullet:
            bx, by = self.bullet["x"], self.bullet["y"]
            for a in self.aliens:
                if not a["alive"]:
                    continue
                r = a["rect"]
                if r.left < bx < r.right and r.top < by < r.bottom:
                    a["alive"] = False
                    self.bullet = None
                    self.score += 10
                    self._spawn_explosion(
                        r.centerx, r.centery, a["color"]
                    )
                    break

        # ── Aliens reaching ship row ──────────────────────────
        reached_bottom = False
        for a in self.aliens:
            if a["alive"] and a["rect"].bottom >= SHIP_Y:
                reached_bottom = True
                break

        if reached_bottom:
            self.lives -= 1
            self.current_action = None
            if self.lives <= 0:
                self.state = "GAMEOVER"
            else:
                self.bullet = None
                self._build_aliens()
            return

        # ── Wave clear ────────────────────────────────────────
        remaining = sum(1 for a in self.aliens if a["alive"])
        if remaining == 0:
            self.level += 1
            self._reset_level()

        # ── Particles ─────────────────────────────────────────
        self._update_particles(dt)

    # ── Drawing ───────────────────────────────────────────────────

    def _draw_stars(self):
        for i, (sx, sy, brightness, speed) in enumerate(self.stars):
            # Slow parallax scroll
            sy += speed * 0.4
            if sy > HEIGHT:
                sy = 0
                sx = random.randint(0, WIDTH)
            self.stars[i] = (sx, sy, brightness, speed)
            c = int(brightness * 180)
            pygame.draw.circle(self.screen, (c, c, c + 40 if c + 40 < 256 else 255),
                               (int(sx), int(sy)), 1)

    def _draw_ship(self):
        """Draw a detailed spaceship polygon with engine glow."""
        cx = self.ship_x + SHIP_WIDTH / 2
        cy = SHIP_Y + SHIP_HEIGHT / 2
        # Engine glow
        glow_surf = pygame.Surface((30, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_surf, (0, 150, 255, 40), (0, 0, 30, 16))
        self.screen.blit(glow_surf, (int(cx) - 15, int(SHIP_Y + SHIP_HEIGHT - 4)))
        # Main body
        points = [
            (cx, SHIP_Y - 6),
            (cx + SHIP_WIDTH / 2 + 2, SHIP_Y + SHIP_HEIGHT),
            (cx + SHIP_WIDTH / 4, SHIP_Y + SHIP_HEIGHT - 4),
            (cx - SHIP_WIDTH / 4, SHIP_Y + SHIP_HEIGHT - 4),
            (cx - SHIP_WIDTH / 2 - 2, SHIP_Y + SHIP_HEIGHT),
        ]
        pygame.draw.polygon(self.screen, CYAN, points)
        # Body highlight
        hi_points = [
            (cx, SHIP_Y - 2),
            (cx + SHIP_WIDTH / 4, SHIP_Y + SHIP_HEIGHT - 6),
            (cx - SHIP_WIDTH / 4, SHIP_Y + SHIP_HEIGHT - 6),
        ]
        pygame.draw.polygon(self.screen, (80, 240, 255), hi_points)
        # Cockpit glow
        pygame.draw.circle(self.screen, WHITE, (int(cx), int(SHIP_Y + 4)), 4)
        pygame.draw.circle(self.screen, (200, 240, 255), (int(cx), int(SHIP_Y + 4)), 2)

    def _draw_alien(self, a):
        """Draw a single alien with an improved sprite-like look."""
        r = a["rect"]
        color = a["color"]
        # Subtle breathing glow
        glow_surf = pygame.Surface((r.width + 8, r.height + 8), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*color, 20), (0, 0, r.width + 8, r.height + 8), border_radius=6)
        self.screen.blit(glow_surf, (r.x - 4, r.y - 4))
        # Body
        pygame.draw.rect(self.screen, color, r, border_radius=5)
        # Eyes
        ew, eh = 5, 4
        eye_y = r.y + 5
        pygame.draw.rect(self.screen, (0, 0, 0),
                         (r.x + 6, eye_y, ew, eh), border_radius=2)
        pygame.draw.rect(self.screen, (0, 0, 0),
                         (r.right - 6 - ew, eye_y, ew, eh), border_radius=2)
        # Eye shine
        pygame.draw.rect(self.screen, (255, 255, 255),
                         (r.x + 7, eye_y, 2, 2))
        pygame.draw.rect(self.screen, (255, 255, 255),
                         (r.right - 6 - ew + 1, eye_y, 2, 2))
        # Top highlight
        highlight = tuple(min(c + 80, 255) for c in color)
        pygame.draw.line(self.screen, highlight,
                         (r.x + 3, r.y + 2), (r.right - 3, r.y + 2), 1)
        # Bottom legs
        leg_color = tuple(max(0, c - 30) for c in color)
        for lx in [r.x + 4, r.x + 12, r.right - 16, r.right - 8]:
            pygame.draw.rect(self.screen, leg_color, (lx, r.bottom - 2, 3, 4))

    def _draw_bullet(self):
        if self.bullet is None:
            return
        bx, by = int(self.bullet["x"]), int(self.bullet["y"])
        # Glow
        glow_surf = pygame.Surface((12, 20), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (255, 255, 200, 80), (2, 2, 8, 16), border_radius=4)
        self.screen.blit(glow_surf, (bx - 6, by - 10))
        # Core
        pygame.draw.rect(self.screen, WHITE,
                         (bx - BULLET_W // 2, by - BULLET_H, BULLET_W, BULLET_H),
                         border_radius=1)

    def _draw_particles(self):
        for p in self.particles:
            alpha = max(0, min(255, int(255 * (p["life"] / 0.7))))
            size = max(1, int(p["size"] * (p["life"] / 0.7)))
            color = tuple(min(255, c) for c in p["color"])
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*color, alpha), (size, size), size)
            self.screen.blit(surf, (int(p["x"]) - size, int(p["y"]) - size))

    def _draw_hud(self):
        """Score / Level / Lives header with background."""
        # HUD background
        hud_bg = pygame.Surface((WIDTH, 40), pygame.SRCALPHA)
        hud_bg.fill((8, 8, 40, 180))
        self.screen.blit(hud_bg, (0, 0))
        # Score
        score_txt = self.font_small.render(f"SCORE  {self.score:05d}", True, WHITE)
        self.screen.blit(score_txt, (15, 12))
        # Level
        level_txt = self.font_small.render(f"LEVEL {self.level}", True, YELLOW)
        lw = level_txt.get_width()
        self.screen.blit(level_txt, (WIDTH // 2 - lw // 2, 12))
        # Lives
        lives_txt = self.font_small.render(f"LIVES  {self.lives}", True, CYAN)
        self.screen.blit(lives_txt, (WIDTH - lives_txt.get_width() - 15, 12))
        # Separator line with glow
        pygame.draw.line(self.screen, (30, 40, 80), (0, 39), (WIDTH, 39), 1)

    def draw(self):
        self.screen.fill(DARK_BLUE)
        self._draw_stars()
        self._draw_hud()

        # Aliens
        for a in self.aliens:
            if a["alive"]:
                self._draw_alien(a)

        # Ship
        self._draw_ship()

        # Bullet
        self._draw_bullet()

        # Particles
        self._draw_particles()

        # Overlay text for non-play states
        if self.state == "GAMEOVER":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((180, 0, 0, 80))
            self.screen.blit(overlay, (0, 0))
            t = self.font_large.render("GAME OVER", True, RED)
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 40))
            t2 = self.font_small.render(f"Final Score: {self.score}", True, WHITE)
            self.screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, HEIGHT // 2 + 20))
            t3 = self.font_small.render("PRESS SPACE TO RESTART", True, WHITE)
            self.screen.blit(t3, (WIDTH // 2 - t3.get_width() // 2, HEIGHT // 2 + 55))
        elif self.state == "PAUSE":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))
            t = self.font_large.render("PAUSED", True, YELLOW)
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 20))
        elif self.state == "TITLE":
            t = self.font_medium.render("PRESS SPACE TO START", True, WHITE)
            self.screen.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 + 80))

        pygame.display.flip()

    # ── Main loop ─────────────────────────────────────────────────

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            self.step(dt)
            self.draw()


if __name__ == "__main__":
    game = SpaceInvaders()
    game.run()
