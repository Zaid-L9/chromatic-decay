"""
CHROMATIC DECAY v3.0 - "SYSTEM FAILURE" EDITION
Abstract survival bullet hell with enhanced visuals.
"""

import pygame
import random
import math
import sys
from dataclasses import dataclass
from typing import List, Tuple
from enum import Enum

pygame.init()

WIDTH, HEIGHT = 800, 600
FPS = 60

VOID_BLACK = (5, 5, 8)
GRID_DARK = (26, 26, 36)
GRID_LIGHT = (45, 45, 68)
PLAYER_WHITE = (255, 255, 255)
PLAYER_CYAN = (0, 240, 255)
ENEMY_RED = (255, 0, 60)
ENEMY_DARK = (138, 0, 32)
ENEMY_MAGENTA = (255, 0, 153)
PICKUP_GREEN = (0, 255, 157)
POWERUP_YELLOW = (255, 230, 0)
TEXT_WHITE = (224, 224, 224)
UI_ACCENT = (110, 87, 255)
UI_CRITICAL = (255, 42, 42)
INACTIVE_GREY = (64, 64, 64)

Color = Tuple[int, int, int]


class PowerUpType(Enum):
    DATA_PURGE = 1
    TIME_DILATION = 2


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0, min(1, t))


def lerp_color(color1: Color, color2: Color, t: float) -> Color:
    t = max(0, min(1, t))
    return (
        int(color1[0] + (color2[0] - color1[0]) * t),
        int(color1[1] + (color2[1] - color1[1]) * t),
        int(color1[2] + (color2[2] - color1[2]) * t),
    )


def desaturate(color: Color, amount: float) -> Color:
    grey = int(sum(color) / 3)
    return lerp_color(color, (grey, grey, grey), amount)


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def create_vignette_surface(width: int, height: int) -> pygame.Surface:
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    cx, cy = width // 2, height // 2
    max_dist = math.sqrt(cx * cx + cy * cy)
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            alpha = int((dist / max_dist) ** 1.5 * 180)
            alpha = min(200, alpha)
            pygame.draw.rect(surface, (0, 0, 0, alpha), (x, y, 4, 4))
    return surface


def create_scanline_surface(width: int, height: int) -> pygame.Surface:
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(0, height, 3):
        pygame.draw.line(surface, (0, 0, 0, 25), (0, y), (width, y))
    return surface


def create_noise_surface(width: int, height: int) -> pygame.Surface:
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    for _ in range(500):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        grey = random.randint(20, 40)
        surface.set_at((x, y), (grey, grey, grey, random.randint(5, 15)))
    return surface


@dataclass
class DustParticle:
    x: float
    y: float
    speed: float
    alpha: int
    size: int

    def update(self, dt: float):
        self.y -= self.speed * dt
        if self.y < -10:
            self.y = HEIGHT + 10
            self.x = random.uniform(0, WIDTH)

    def draw(self, surface: pygame.Surface, offset: Tuple[float, float]):
        px = int(self.x + offset[0] * 0.3)
        py = int(self.y + offset[1] * 0.3)
        color = (*GRID_DARK, self.alpha)
        s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        s.fill(color)
        surface.blit(s, (px, py))


@dataclass
class GhostTrail:
    x: float
    y: float
    rotation: float
    scale: float
    alpha: float
    life: float
    max_life: float

    def update(self, dt: float):
        self.life -= dt
        t = 1 - (self.life / self.max_life)
        self.alpha = int(128 * (1 - t))
        self.scale = 1.0 - t * 0.5

    def draw(self, surface: pygame.Surface, offset: Tuple[float, float]):
        if self.alpha <= 0:
            return
        size = int(20 * self.scale)
        points = []
        for angle in [45, 135, 225, 315]:
            rad = math.radians(angle + self.rotation)
            px = self.x + offset[0] + math.cos(rad) * size * 0.7
            py = self.y + offset[1] + math.sin(rad) * size * 0.7
            points.append((px, py))

        ghost_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        adjusted_points = [
            (p[0] - self.x - offset[0] + size, p[1] - self.y - offset[1] + size)
            for p in points
        ]
        pygame.draw.polygon(
            ghost_surf, (*PLAYER_CYAN, int(self.alpha)), adjusted_points, 2
        )
        surface.blit(ghost_surf, (self.x + offset[0] - size, self.y + offset[1] - size))


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: Color
    shape: str = "rect"
    rotation: float = 0
    rot_speed: float = 0

    def update(self, dt: float, time_scale: float = 1.0):
        self.x += self.vx * dt * time_scale
        self.y += self.vy * dt * time_scale
        self.vx *= 0.92
        self.vy *= 0.92
        self.life -= dt
        self.rotation += self.rot_speed * dt

    def draw(self, surface: pygame.Surface, offset: Tuple[float, float]):
        if self.life <= 0:
            return
        alpha = self.life / self.max_life
        color = lerp_color(self.color, VOID_BLACK, 1 - alpha)
        size = max(1, int(self.size * alpha))
        px, py = int(self.x + offset[0]), int(self.y + offset[1])

        if self.shape == "line":
            end_x = px + math.cos(self.rotation) * size * 2
            end_y = py + math.sin(self.rotation) * size * 2
            pygame.draw.line(
                surface, color, (px, py), (end_x, end_y), max(1, size // 2)
            )
        elif self.shape == "hollow":
            pygame.draw.rect(
                surface, color, (px - size, py - size, size * 2, size * 2), 1
            )
        else:
            pygame.draw.rect(surface, color, (px, py, size, size))


@dataclass
class GrazeSpark:
    x: float
    y: float
    target_x: float
    target_y: float
    life: float = 0.3

    def update(self, dt: float, player_x: float, player_y: float):
        self.target_x = player_x
        self.target_y = player_y
        t = 1 - (self.life / 0.3)
        self.x += (self.target_x - self.x) * t * 0.4
        self.y += (self.target_y - self.y) * t * 0.4
        self.life -= dt

    def draw(self, surface: pygame.Surface, offset: Tuple[float, float]):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / 0.3))
        size = max(1, int(4 * (self.life / 0.3)))
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        s.fill((*POWERUP_YELLOW, alpha))
        surface.blit(s, (int(self.x + offset[0]), int(self.y + offset[1])))


@dataclass
class ImplosionLine:
    angle: float
    radius: float
    target_radius: float
    color: Color
    life: float = 0.3

    def update(self, dt: float):
        self.radius = lerp(self.radius, self.target_radius, dt * 8)
        self.life -= dt

    def draw(
        self, surface: pygame.Surface, cx: float, cy: float, offset: Tuple[float, float]
    ):
        if self.life <= 0:
            return
        alpha = int(255 * (self.life / 0.3))
        x1 = cx + offset[0] + math.cos(self.angle) * self.radius
        y1 = cy + offset[1] + math.sin(self.angle) * self.radius
        x2 = cx + offset[0] + math.cos(self.angle) * (self.radius + 15)
        y2 = cy + offset[1] + math.sin(self.angle) * (self.radius + 15)
        color = (*self.color, alpha)
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(s, color, (x1, y1), (x2, y2), 2)
        surface.blit(s, (0, 0))


class Player:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.size = 20
        self.core_size = 12
        self.speed = 600
        self.friction = 0.92
        self.health = 100
        self.max_health = 100
        self.rotation = 0
        self.shell_rotation = 0
        self.invincible_timer = 0.0
        self.chromatic_timer = 0.0
        self.dash_cooldown = 0.0
        self.dash_cooldown_max = 1.0
        self.is_dashing = False
        self.dash_timer = 0.0
        self.dash_duration = 0.15
        self.dash_distance = 180
        self.dash_dir_x = 0.0
        self.dash_dir_y = 0.0
        self.last_move_x = 1.0
        self.last_move_y = 0.0
        self.ghost_trails: List[GhostTrail] = []
        self.ghost_spawn_timer = 0.0
        self.aura_pulse = 0.0

    def dash(self):
        if self.dash_cooldown <= 0 and not self.is_dashing:
            self.is_dashing = True
            self.dash_timer = self.dash_duration
            self.dash_cooldown = self.dash_cooldown_max
            self.invincible_timer = self.dash_duration
            mag = math.sqrt(self.last_move_x**2 + self.last_move_y**2)
            if mag > 0:
                self.dash_dir_x = self.last_move_x / mag
                self.dash_dir_y = self.last_move_y / mag
            else:
                self.dash_dir_x, self.dash_dir_y = 1, 0
            self.chromatic_timer = 0.15
            return True
        return False

    def update(self, dt: float, keys, time_scale: float = 1.0):
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt

        self.ghost_spawn_timer += dt
        if self.ghost_spawn_timer >= 0.05:
            self.ghost_spawn_timer = 0
            if abs(self.vx) > 10 or abs(self.vy) > 10 or self.is_dashing:
                self.ghost_trails.append(
                    GhostTrail(self.x, self.y, self.shell_rotation, 1.0, 128, 0.4, 0.4)
                )

        for ghost in self.ghost_trails[:]:
            ghost.update(dt)
            if ghost.life <= 0:
                self.ghost_trails.remove(ghost)

        if self.is_dashing:
            self.dash_timer -= dt
            dash_speed = self.dash_distance / self.dash_duration
            self.x += self.dash_dir_x * dash_speed * dt
            self.y += self.dash_dir_y * dash_speed * dt
            if self.dash_timer <= 0:
                self.is_dashing = False
        else:
            ax, ay = 0, 0
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                ay = -self.speed
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                ay = self.speed
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                ax = -self.speed
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                ax = self.speed

            if ax != 0 or ay != 0:
                self.last_move_x, self.last_move_y = ax, ay

            self.vx += ax * dt * time_scale
            self.vy += ay * dt * time_scale
            self.vx *= self.friction
            self.vy *= self.friction
            self.x += self.vx * dt * time_scale
            self.y += self.vy * dt * time_scale

        self.x = max(self.size, min(WIDTH - self.size, self.x))
        self.y = max(self.size, min(HEIGHT - self.size, self.y))

        self.rotation += 180 * dt
        self.shell_rotation -= 120 * dt
        self.aura_pulse += dt * 2 * math.pi

        if self.invincible_timer > 0:
            self.invincible_timer -= dt
        if self.chromatic_timer > 0:
            self.chromatic_timer -= dt

    def take_damage(self, amount: int) -> bool:
        if self.invincible_timer <= 0 and not self.is_dashing:
            self.health -= amount
            self.invincible_timer = 0.5
            self.chromatic_timer = 0.2
            return True
        return False

    def draw(self, surface: pygame.Surface, offset: Tuple[float, float]):
        px, py = self.x + offset[0], self.y + offset[1]

        for ghost in self.ghost_trails:
            ghost.draw(surface, offset)

        aura_size = int(self.size * 3 * (1 + 0.05 * math.sin(self.aura_pulse)))
        aura_surf = pygame.Surface((aura_size * 2, aura_size * 2), pygame.SRCALPHA)
        for i in range(3):
            r = aura_size - i * (aura_size // 3)
            alpha = 20 - i * 6
            color = lerp_color(PLAYER_WHITE, PLAYER_CYAN, i / 2)
            pygame.draw.circle(
                aura_surf, (*color, max(0, alpha)), (aura_size, aura_size), r
            )
        surface.blit(
            aura_surf, (px - aura_size, py - aura_size), special_flags=pygame.BLEND_ADD
        )

        if self.chromatic_timer > 0:
            self._draw_shape(surface, px - 3, py - 3, ENEMY_RED)
            self._draw_shape(surface, px + 3, py + 3, PLAYER_CYAN)

        if self.invincible_timer <= 0 or int(self.invincible_timer * 15) % 2 == 0:
            self._draw_shape(surface, px, py, PLAYER_WHITE)

        self._draw_dash_indicator(surface, px, py)

    def _draw_shape(self, surface: pygame.Surface, px: float, py: float, color: Color):
        core_points = []
        for angle in [45, 135, 225, 315]:
            rad = math.radians(angle + self.rotation)
            x = px + math.cos(rad) * self.core_size * 0.5
            y = py + math.sin(rad) * self.core_size * 0.5
            core_points.append((x, y))
        pygame.draw.polygon(surface, color, core_points)

        shell_points = []
        for angle in [45, 135, 225, 315]:
            rad = math.radians(angle + self.shell_rotation)
            x = px + math.cos(rad) * self.size * 0.7
            y = py + math.sin(rad) * self.size * 0.7
            shell_points.append((x, y))
        pygame.draw.polygon(surface, PLAYER_CYAN, shell_points, 2)

    def _draw_dash_indicator(self, surface: pygame.Surface, px: float, py: float):
        dash_ready = self.dash_cooldown <= 0
        indicator_size = self.size + 12

        if dash_ready:
            for i in range(4):
                angle = 45 + i * 90 + self.shell_rotation
                rad1 = math.radians(angle)
                rad2 = math.radians(angle + 90)
                x1 = px + math.cos(rad1) * indicator_size * 0.6
                y1 = py + math.sin(rad1) * indicator_size * 0.6
                x2 = px + math.cos(rad2) * indicator_size * 0.6
                y2 = py + math.sin(rad2) * indicator_size * 0.6
                pygame.draw.line(surface, PLAYER_CYAN, (x1, y1), (x2, y2), 1)
        else:
            progress = 1 - (self.dash_cooldown / self.dash_cooldown_max)
            arc_angle = progress * 360
            rect = pygame.Rect(
                px - indicator_size * 0.6,
                py - indicator_size * 0.6,
                indicator_size * 1.2,
                indicator_size * 1.2,
            )
            if arc_angle > 0:
                pygame.draw.arc(
                    surface, INACTIVE_GREY, rect, 0, math.radians(arc_angle), 1
                )


class StaticEater:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.speed = random.uniform(50, 90)
        self.alive = True
        self.size = 24
        self.enemy_type = "static_eater"
        self.spawn_scale = 0.0
        self.spawn_timer = 0.3
        self.jitter_offset = (0, 0)
        self.inner_rotation = 0

    def update(
        self, dt: float, player_x: float, player_y: float, time_scale: float = 1.0
    ):
        if self.spawn_timer > 0:
            self.spawn_timer -= dt
            t = 1 - (self.spawn_timer / 0.3)
            self.spawn_scale = min(1.2, t * 1.4) if t < 0.8 else 1.0
            return

        dx, dy = player_x - self.x, player_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            self.x += (dx / dist) * self.speed * dt * time_scale
            self.y += (dy / dist) * self.speed * dt * time_scale

        if random.random() < 0.1:
            self.jitter_offset = (random.randint(-2, 2), random.randint(-2, 2))
        else:
            self.jitter_offset = (0, 0)

        self.inner_rotation += 400 * dt

    def draw(
        self, surface: pygame.Surface, offset: Tuple[float, float], desaturation: float
    ):
        color = desaturate(ENEMY_RED, desaturation)
        dark_color = desaturate(ENEMY_DARK, desaturation)

        px = self.x + offset[0] + self.jitter_offset[0]
        py = self.y + offset[1] + self.jitter_offset[1]
        size = int(self.size * self.spawn_scale)
        half = size // 2

        pygame.draw.rect(surface, color, (px - half, py - half, size, size))

        inner_size = size // 2
        pygame.draw.rect(
            surface,
            VOID_BLACK,
            (px - inner_size // 2, py - inner_size // 2, inner_size, inner_size),
        )

        core_size = 4
        core_points = []
        for angle in [45, 135, 225, 315]:
            rad = math.radians(angle + self.inner_rotation)
            x = px + math.cos(rad) * core_size
            y = py + math.sin(rad) * core_size
            core_points.append((x, y))
        pygame.draw.polygon(surface, color, core_points)

    def get_collision_radius(self) -> float:
        return self.size * 0.4 * self.spawn_scale


class Vectro:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.speed = 160
        self.turn_rate = 1.5
        self.size = 32
        self.alive = True
        self.enemy_type = "vectro"
        self.angle = random.uniform(0, 360)
        self.charge_timer = 0.0
        self.is_charging = False
        self.target_x = 0.0
        self.target_y = 0.0
        self.spawn_scale = 0.0
        self.spawn_timer = 0.3
        self.thruster_particles: List[Tuple[float, float, float]] = []

    def update(
        self, dt: float, player_x: float, player_y: float, time_scale: float = 1.0
    ):
        if self.spawn_timer > 0:
            self.spawn_timer -= dt
            t = 1 - (self.spawn_timer / 0.3)
            self.spawn_scale = min(1.2, t * 1.4) if t < 0.8 else 1.0
            return

        self.charge_timer += dt * time_scale

        if self.charge_timer >= 1.5:
            self.charge_timer = 0
            self.is_charging = True
            self.target_x, self.target_y = player_x, player_y
            dx, dy = self.target_x - self.x, self.target_y - self.y
            self.angle = math.degrees(math.atan2(dy, dx))

        if self.is_charging:
            self.x += (
                math.cos(math.radians(self.angle)) * self.speed * 1.5 * dt * time_scale
            )
            self.y += (
                math.sin(math.radians(self.angle)) * self.speed * 1.5 * dt * time_scale
            )
            if distance(self.x, self.y, self.target_x, self.target_y) < 20:
                self.is_charging = False
        else:
            dx, dy = player_x - self.x, player_y - self.y
            target_angle = math.degrees(math.atan2(dy, dx))
            angle_diff = (target_angle - self.angle + 180) % 360 - 180
            self.angle += angle_diff * self.turn_rate * dt * time_scale
            self.x += (
                math.cos(math.radians(self.angle)) * self.speed * 0.5 * dt * time_scale
            )
            self.y += (
                math.sin(math.radians(self.angle)) * self.speed * 0.5 * dt * time_scale
            )

        rad = math.radians(self.angle + 180)
        tx = self.x + math.cos(rad) * self.size * 0.5
        ty = self.y + math.sin(rad) * self.size * 0.5
        self.thruster_particles.append((tx, ty, 0.2))
        self.thruster_particles = [
            (x, y, l - dt) for x, y, l in self.thruster_particles if l > 0
        ]

    def draw(
        self, surface: pygame.Surface, offset: Tuple[float, float], desaturation: float
    ):
        color = desaturate(ENEMY_RED, desaturation)
        dark_color = desaturate(ENEMY_DARK, desaturation)

        for tx, ty, life in self.thruster_particles:
            alpha = int(200 * (life / 0.2))
            size = int(4 * (life / 0.2))
            if size > 0:
                s = pygame.Surface((size, size), pygame.SRCALPHA)
                s.fill((*POWERUP_YELLOW, alpha))
                surface.blit(s, (int(tx + offset[0]), int(ty + offset[1])))

        rad = math.radians(self.angle)
        size = self.size * self.spawn_scale
        tip_x = self.x + offset[0] + math.cos(rad) * size
        tip_y = self.y + offset[1] + math.sin(rad) * size
        left_x = self.x + offset[0] + math.cos(rad + 2.6) * size * 0.5
        left_y = self.y + offset[1] + math.sin(rad + 2.6) * size * 0.5
        right_x = self.x + offset[0] + math.cos(rad - 2.6) * size * 0.5
        right_y = self.y + offset[1] + math.sin(rad - 2.6) * size * 0.5

        pygame.draw.polygon(
            surface, dark_color, [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)]
        )
        pygame.draw.polygon(
            surface, color, [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)], 2
        )

    def get_collision_radius(self) -> float:
        return self.size * 0.4 * self.spawn_scale


class Scanner:
    def __init__(self, horizontal: bool = True):
        self.horizontal = horizontal
        self.size = 20
        self.alive = True
        self.enemy_type = "scanner"
        self.warning_timer = 1.0
        self.is_warning = True
        self.sweep_speed = 200
        self.flicker_timer = 0.0
        self.eye_pos = 0.0
        self.eye_dir = 1

        if horizontal:
            self.x, self.y = 0, -50
            self.width, self.height = WIDTH, self.size
        else:
            self.x, self.y = -50, 0
            self.width, self.height = self.size, HEIGHT

    def update(
        self, dt: float, player_x: float, player_y: float, time_scale: float = 1.0
    ):
        self.flicker_timer += dt * 15
        self.eye_pos += self.eye_dir * dt * 100
        if self.eye_pos > 30 or self.eye_pos < -30:
            self.eye_dir *= -1

        if self.is_warning:
            self.warning_timer -= dt
            if self.warning_timer <= 0:
                self.is_warning = False
                self.y = 0 if self.horizontal else self.y
                self.x = 0 if not self.horizontal else self.x
        else:
            if self.horizontal:
                self.y += self.sweep_speed * dt * time_scale
                if self.y > HEIGHT:
                    self.alive = False
            else:
                self.x += self.sweep_speed * dt * time_scale
                if self.x > WIDTH:
                    self.alive = False

    def draw(
        self, surface: pygame.Surface, offset: Tuple[float, float], desaturation: float
    ):
        color = desaturate(ENEMY_RED, desaturation)

        if self.is_warning:
            if int(self.flicker_timer) % 2 == 0:
                if self.horizontal:
                    pygame.draw.line(surface, color, (0, 5), (WIDTH, 5), 3)
                else:
                    pygame.draw.line(surface, color, (5, 0), (5, HEIGHT), 3)
        else:
            flicker = math.sin(self.flicker_timer) * 2
            if self.horizontal:
                h = int(self.height + flicker)
                rect = pygame.Rect(
                    self.x + offset[0], self.y + offset[1], self.width, h
                )
            else:
                w = int(self.width + flicker)
                rect = pygame.Rect(
                    self.x + offset[0], self.y + offset[1], w, self.height
                )

            s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            s.fill((*color, 120))
            surface.blit(s, rect.topleft)

            if self.horizontal:
                eye_x = WIDTH // 2 + self.eye_pos
                eye_y = self.y + offset[1] + self.height // 2
            else:
                eye_x = self.x + offset[0] + self.width // 2
                eye_y = HEIGHT // 2 + self.eye_pos
            pygame.draw.line(
                surface, PLAYER_WHITE, (eye_x, eye_y - 5), (eye_x, eye_y + 5), 2
            )

    def check_collision(
        self, player_x: float, player_y: float, player_size: float
    ) -> bool:
        if self.is_warning:
            return False
        if self.horizontal:
            return (
                self.y < player_y + player_size / 2
                and self.y + self.height > player_y - player_size / 2
            )
        return (
            self.x < player_x + player_size / 2
            and self.x + self.width > player_x - player_size / 2
        )

    def get_collision_radius(self) -> float:
        return 0


class Node:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.size = 20
        self.alive = True
        self.enemy_type = "node"
        self.rotation = 0
        self.pulse_timer = 0.0
        self.pulse_interval = 2.0
        self.shockwave_radius = 0.0
        self.shockwave_active = False
        self.shockwave_max = 150
        self.shockwave_speed = 400
        self.core_size = 5
        self.spawn_scale = 0.0
        self.spawn_timer = 0.3

    def update(
        self, dt: float, player_x: float, player_y: float, time_scale: float = 1.0
    ):
        if self.spawn_timer > 0:
            self.spawn_timer -= dt
            t = 1 - (self.spawn_timer / 0.3)
            self.spawn_scale = min(1.2, t * 1.4) if t < 0.8 else 1.0
            return

        self.rotation += 30 * dt * time_scale
        self.pulse_timer += dt * time_scale
        self.core_size = 5 + math.sin(self.pulse_timer * 3) * 10

        if self.pulse_timer >= self.pulse_interval:
            self.pulse_timer = 0
            self.shockwave_active = True
            self.shockwave_radius = self.size

        if self.shockwave_active:
            self.shockwave_radius += self.shockwave_speed * dt * time_scale
            if self.shockwave_radius >= self.shockwave_max:
                self.shockwave_active = False
                self.shockwave_radius = 0

    def draw(
        self, surface: pygame.Surface, offset: Tuple[float, float], desaturation: float
    ):
        color = desaturate(ENEMY_RED, desaturation)
        px, py = self.x + offset[0], self.y + offset[1]
        size = self.size * self.spawn_scale

        if self.shockwave_active:
            alpha = int(150 * (1 - self.shockwave_radius / self.shockwave_max))
            points = []
            for i in range(6):
                angle = math.radians(self.rotation + i * 60)
                x = px + math.cos(angle) * self.shockwave_radius
                y = py + math.sin(angle) * self.shockwave_radius
                points.append((x, y))
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(s, (*color, alpha), points, 2)
            surface.blit(s, (0, 0))

        points = []
        for i in range(6):
            angle = math.radians(self.rotation + i * 60)
            x = px + math.cos(angle) * size
            y = py + math.sin(angle) * size
            points.append((x, y))
        pygame.draw.polygon(surface, color, points, 3)

        core_points = []
        for i in range(6):
            angle = math.radians(-self.rotation + i * 60)
            cs = max(3, self.core_size * self.spawn_scale)
            x = px + math.cos(angle) * cs
            y = py + math.sin(angle) * cs
            core_points.append((x, y))
        pygame.draw.polygon(surface, color, core_points)

    def check_collision(
        self, player_x: float, player_y: float, player_size: float
    ) -> bool:
        dist = distance(self.x, self.y, player_x, player_y)
        if dist < self.size * self.spawn_scale + player_size / 2:
            return True
        if self.shockwave_active:
            ring_inner = self.shockwave_radius - 15
            ring_outer = self.shockwave_radius + 15
            if ring_inner < dist < ring_outer:
                return True
        return False

    def get_collision_radius(self) -> float:
        return self.size * self.spawn_scale


class Prism:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.rotation = random.uniform(0, 360)
        self.pulse_timer = random.uniform(0, math.pi * 2)
        self.size = 15
        self.alive = True
        self.glow_alpha = 0

    def update(self, dt: float, time_scale: float = 1.0):
        self.rotation += 100 * dt * time_scale
        self.pulse_timer += dt * 4
        self.glow_alpha = int(50 + 30 * math.sin(self.pulse_timer))

    def draw(
        self, surface: pygame.Surface, offset: Tuple[float, float], desaturation: float
    ):
        color = desaturate(PICKUP_GREEN, desaturation)
        scale = 1.0 + math.sin(self.pulse_timer) * 0.2
        size = self.size * scale
        px, py = self.x + offset[0], self.y + offset[1]

        glow_surf = pygame.Surface((int(size * 4), int(size * 4)), pygame.SRCALPHA)
        pygame.draw.circle(
            glow_surf,
            (*color, self.glow_alpha),
            (int(size * 2), int(size * 2)),
            int(size * 1.5),
        )
        surface.blit(
            glow_surf, (px - size * 2, py - size * 2), special_flags=pygame.BLEND_ADD
        )

        points = []
        for i in range(3):
            angle = math.radians(self.rotation + i * 120)
            points.append((px + math.cos(angle) * size, py + math.sin(angle) * size))
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, PLAYER_WHITE, points, 2)


class PowerUp:
    def __init__(self, x: float, y: float, power_type: PowerUpType):
        self.x = x
        self.y = y
        self.power_type = power_type
        self.pulse_timer = 0
        self.size = 18
        self.alive = True

    def update(self, dt: float, time_scale: float = 1.0):
        self.pulse_timer += dt * 3

    def draw(
        self, surface: pygame.Surface, offset: Tuple[float, float], desaturation: float
    ):
        scale = 1.0 + math.sin(self.pulse_timer) * 0.15
        size = self.size * scale
        px, py = self.x + offset[0], self.y + offset[1]

        if self.power_type == PowerUpType.DATA_PURGE:
            color = desaturate(POWERUP_YELLOW, desaturation)
            glow_surf = pygame.Surface((int(size * 4), int(size * 4)), pygame.SRCALPHA)
            pygame.draw.circle(
                glow_surf, (*color, 40), (int(size * 2), int(size * 2)), int(size * 1.5)
            )
            surface.blit(
                glow_surf,
                (px - size * 2, py - size * 2),
                special_flags=pygame.BLEND_ADD,
            )

            points = [
                (px, py - size),
                (px + size, py),
                (px, py + size),
                (px - size, py),
            ]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.polygon(surface, PLAYER_WHITE, points, 2)
        else:
            color = desaturate(PLAYER_CYAN, desaturation)
            tri_size = size * 0.6
            pygame.draw.polygon(
                surface,
                color,
                [
                    (px, py - tri_size),
                    (px - tri_size * 0.7, py),
                    (px + tri_size * 0.7, py),
                ],
            )
            pygame.draw.polygon(
                surface,
                color,
                [
                    (px, py + tri_size),
                    (px - tri_size * 0.7, py),
                    (px + tri_size * 0.7, py),
                ],
            )


@dataclass
class Wave:
    name: str
    static_eaters: int = 0
    vectros: int = 0
    scanners: int = 0
    nodes: int = 0
    spawn_interval: float = 1.5


WAVES = [
    Wave("BOOT SEQUENCE", static_eaters=8),
    Wave("PACKET LOSS", static_eaters=5, vectros=3, spawn_interval=1.2),
    Wave("FIREWALL", static_eaters=6, scanners=2, spawn_interval=1.0),
    Wave("CORRUPTED SECTOR", vectros=5, nodes=2, spawn_interval=0.8),
    Wave(
        "SYSTEM CRASH",
        static_eaters=8,
        vectros=4,
        scanners=2,
        nodes=2,
        spawn_interval=0.6,
    ),
]


class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("CHROMATIC DECAY")
        self.clock = pygame.time.Clock()

        self.font_large = pygame.font.SysFont("Consolas", 80, bold=True)
        self.font_medium = pygame.font.SysFont("Consolas", 40, bold=True)
        self.font_small = pygame.font.SysFont("Consolas", 24)
        self.font_tiny = pygame.font.SysFont("Consolas", 16)
        self.font_score_bg = pygame.font.SysFont("Consolas", 150, bold=True)
        self.font_multiplier = pygame.font.SysFont("Consolas", 36, bold=True)

        self.vignette = create_vignette_surface(WIDTH, HEIGHT)
        self.scanlines = create_scanline_surface(WIDTH, HEIGHT)
        self.noise = create_noise_surface(WIDTH, HEIGHT)
        self.noise_timer = 0

        self.dust_particles = [
            DustParticle(
                random.uniform(0, WIDTH),
                random.uniform(0, HEIGHT),
                random.uniform(5, 15),
                random.randint(30, 80),
                random.randint(1, 3),
            )
            for _ in range(40)
        ]

        self.state = "menu"
        self.menu_time = 0
        self.reset_game()

    def reset_game(self):
        self.player = Player(WIDTH // 2, HEIGHT // 2)
        self.enemies: List = []
        self.prisms: List[Prism] = []
        self.powerups: List[PowerUp] = []
        self.particles: List[Particle] = []
        self.graze_sparks: List[GrazeSpark] = []
        self.implosion_lines: List[ImplosionLine] = []
        self.score = 0
        self.time_survived = 0
        self.spawn_timer = 0
        self.prism_spawn_timer = 0
        self.powerup_spawn_timer = 0
        self.screen_shake = 0
        self.shake_intensity = 0
        self.shake_rotation = 0
        self.beat_timer = 0
        self.hitstop_frames = 0
        self.time_dilation_timer = 0
        self.flash_timer = 0
        self.flash_color = PLAYER_WHITE
        self.multiplier = 1.0
        self.multiplier_decay_timer = 0
        self.graze_distance = 30
        self.current_wave = 0
        self.wave_timer = 0
        self.wave_duration = 20
        self.wave_transition = False
        self.wave_transition_timer = 0
        self.enemies_to_spawn = {
            "static_eater": 0,
            "vectro": 0,
            "scanner": 0,
            "node": 0,
        }
        self.cycle = 1
        self.death_particles: List[Particle] = []
        self.low_health_pulse = 0
        self.grid_distortions: List[Tuple[float, float, float, float]] = []
        self.start_wave(0)

    def start_wave(self, wave_index: int):
        self.current_wave = wave_index % len(WAVES)
        wave = WAVES[self.current_wave]
        speed_mult = 1.0 + (self.cycle - 1) * 0.5
        self.enemies_to_spawn = {
            "static_eater": int(wave.static_eaters * speed_mult),
            "vectro": int(wave.vectros * speed_mult),
            "scanner": wave.scanners,
            "node": wave.nodes,
        }
        self.wave_timer = 0
        self.spawn_timer = 0

    def get_time_scale(self) -> float:
        return 0.5 if self.time_dilation_timer > 0 else 1.0

    def spawn_enemy_at_edge(self, enemy_class):
        side = random.randint(0, 3)
        if side == 0:
            x, y = random.randint(0, WIDTH), -30
        elif side == 1:
            x, y = WIDTH + 30, random.randint(0, HEIGHT)
        elif side == 2:
            x, y = random.randint(0, WIDTH), HEIGHT + 30
        else:
            x, y = -30, random.randint(0, HEIGHT)
        return enemy_class(x, y)

    def spawn_prism(self):
        self.prisms.append(
            Prism(random.randint(50, WIDTH - 50), random.randint(50, HEIGHT - 50))
        )

    def spawn_powerup(self):
        power_type = random.choice([PowerUpType.DATA_PURGE, PowerUpType.TIME_DILATION])
        self.powerups.append(
            PowerUp(
                random.randint(80, WIDTH - 80),
                random.randint(80, HEIGHT - 80),
                power_type,
            )
        )

    def spawn_particles(self, x: float, y: float, color: Color, count: int = 20):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(80, 250)
            shape = random.choice(["rect", "line", "hollow"])
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=random.uniform(0.3, 0.6),
                    max_life=0.5,
                    size=random.uniform(2, 6),
                    color=color,
                    shape=shape,
                    rotation=angle,
                    rot_speed=random.uniform(-5, 5),
                )
            )

    def spawn_implosion(self, x: float, y: float, color: Color):
        for i in range(10):
            angle = (i / 10) * math.pi * 2
            self.implosion_lines.append(ImplosionLine(angle, 60, 0, color))

    def add_grid_distortion(self, x: float, y: float, strength: float):
        self.grid_distortions.append((x, y, strength, 0.5))

    def trigger_flash(self, color: Color = PLAYER_WHITE, duration: float = 0.1):
        self.flash_timer = duration
        self.flash_color = color

    def trigger_data_purge(self):
        self.spawn_particles(self.player.x, self.player.y, PLAYER_WHITE, 50)
        self.trigger_flash(PLAYER_WHITE, 0.15)
        self.trigger_shake(20, 0.4)

        for enemy in self.enemies[:]:
            if enemy.enemy_type in ["static_eater", "vectro"]:
                self.spawn_particles(enemy.x, enemy.y, ENEMY_RED, 15)
                self.add_grid_distortion(enemy.x, enemy.y, 30)
                self.score += 50 * int(self.multiplier)
                self.enemies.remove(enemy)
            elif enemy.enemy_type == "node":
                dx, dy = enemy.x - self.player.x, enemy.y - self.player.y
                dist = max(1, distance(enemy.x, enemy.y, self.player.x, self.player.y))
                enemy.x += (dx / dist) * 200
                enemy.y += (dy / dist) * 200

    def trigger_shake(self, intensity: float, duration: float):
        self.shake_intensity = max(self.shake_intensity, intensity)
        self.screen_shake = max(self.screen_shake, duration)
        self.shake_rotation = random.uniform(-2, 2)

    def get_shake_offset(self) -> Tuple[float, float]:
        if self.screen_shake <= 0:
            return (0, 0)
        return (
            random.uniform(-self.shake_intensity, self.shake_intensity),
            random.uniform(-self.shake_intensity, self.shake_intensity),
        )

    def get_desaturation(self) -> float:
        return 1.0 - (self.player.health / self.player.max_health)

    def draw_grid(self, surface: pygame.Surface, offset: Tuple[float, float]):
        health_ratio = self.player.health / self.player.max_health
        if health_ratio > 0.5:
            color = lerp_color(GRID_DARK, PLAYER_CYAN, (health_ratio - 0.5) * 0.5)
        else:
            color = lerp_color(ENEMY_RED, GRID_DARK, health_ratio * 2)

        if self.player.health <= 10 and random.random() < 0.3:
            return

        self.grid_distortions = [
            (x, y, s, l - 1 / 60) for x, y, s, l in self.grid_distortions if l > 0
        ]

        spacing = 50
        for gx in range(0, WIDTH + spacing, spacing):
            for gy in range(0, HEIGHT + spacing, spacing):
                px, py = gx + offset[0], gy + offset[1]

                wave_x = math.sin(self.time_survived * 0.5 + gx * 0.02) * 2
                wave_y = math.cos(self.time_survived * 0.5 + gy * 0.02) * 2

                for dx, dy, strength, life in self.grid_distortions:
                    dist = distance(gx, gy, dx, dy)
                    if dist < strength * 3:
                        push = (1 - dist / (strength * 3)) * strength * (life / 0.5)
                        if dist > 0:
                            wave_x += (gx - dx) / dist * push * 0.5
                            wave_y += (gy - dy) / dist * push * 0.5

                px += wave_x
                py += wave_y

                pygame.draw.line(surface, color, (px - 3, py), (px + 3, py), 1)
                pygame.draw.line(surface, color, (px, py - 3), (px, py + 3), 1)

    def draw_scanlines_overlay(self, surface: pygame.Surface):
        surface.blit(self.scanlines, (0, 0))

    def draw_vignette(self, surface: pygame.Surface):
        health_ratio = self.player.health / self.player.max_health
        if health_ratio < 0.3:
            self.low_health_pulse += 0.1
            pulse = abs(math.sin(self.low_health_pulse))
            tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            alpha = int(30 + pulse * 40)
            tint.fill((100, 0, 0, alpha))
            surface.blit(tint, (0, 0))
        surface.blit(self.vignette, (0, 0))

    def draw_noise(self, surface: pygame.Surface):
        self.noise_timer += 1
        if self.noise_timer >= 3:
            self.noise_timer = 0
            self.noise = create_noise_surface(WIDTH, HEIGHT)
        surface.blit(self.noise, (0, 0), special_flags=pygame.BLEND_ADD)

    def check_graze(self, enemy) -> bool:
        if hasattr(enemy, "is_warning") and enemy.is_warning:
            return False
        if enemy.enemy_type == "scanner":
            return False
        dist = distance(self.player.x, self.player.y, enemy.x, enemy.y)
        collision_dist = enemy.get_collision_radius() + self.player.size * 0.5
        graze_dist = collision_dist + self.graze_distance
        return collision_dist < dist < graze_dist

    def update_game(self, dt: float):
        if self.hitstop_frames > 0:
            self.hitstop_frames -= 1
            return

        time_scale = self.get_time_scale()
        keys = pygame.key.get_pressed()

        self.time_survived += dt
        self.spawn_timer += dt
        self.prism_spawn_timer += dt
        self.powerup_spawn_timer += dt
        self.beat_timer += dt
        self.wave_timer += dt

        if self.beat_timer >= 1.0:
            self.beat_timer = 0

        if self.time_dilation_timer > 0:
            self.time_dilation_timer -= dt
        if self.flash_timer > 0:
            self.flash_timer -= dt

        for dust in self.dust_particles:
            dust.update(dt)

        if self.wave_transition:
            self.wave_transition_timer -= dt
            if self.wave_transition_timer <= 0:
                self.wave_transition = False
                wave_index = self.current_wave + 1
                if wave_index >= len(WAVES):
                    self.cycle += 1
                self.start_wave(wave_index)
        elif self.wave_timer >= self.wave_duration:
            self.wave_transition = True
            self.wave_transition_timer = 2.0

        wave = WAVES[self.current_wave]
        spawn_interval = wave.spawn_interval / self.cycle
        if self.spawn_timer >= spawn_interval and not self.wave_transition:
            self.spawn_timer = 0
            if self.enemies_to_spawn["static_eater"] > 0:
                self.enemies.append(self.spawn_enemy_at_edge(StaticEater))
                self.enemies_to_spawn["static_eater"] -= 1
            if self.enemies_to_spawn["vectro"] > 0 and random.random() < 0.3:
                self.enemies.append(self.spawn_enemy_at_edge(Vectro))
                self.enemies_to_spawn["vectro"] -= 1
            if self.enemies_to_spawn["scanner"] > 0 and random.random() < 0.1:
                self.enemies.append(Scanner(horizontal=random.choice([True, False])))
                self.enemies_to_spawn["scanner"] -= 1
            if self.enemies_to_spawn["node"] > 0 and random.random() < 0.05:
                self.enemies.append(
                    Node(
                        random.randint(100, WIDTH - 100),
                        random.randint(100, HEIGHT - 100),
                    )
                )
                self.enemies_to_spawn["node"] -= 1

        if self.prism_spawn_timer >= 5.0:
            self.prism_spawn_timer = 0
            self.spawn_prism()

        if self.powerup_spawn_timer >= 15.0:
            self.powerup_spawn_timer = 0
            self.spawn_powerup()

        self.player.update(dt, keys, time_scale)

        if self.screen_shake > 0:
            self.screen_shake -= dt
            self.shake_intensity *= 0.88

        self.multiplier_decay_timer += dt
        if self.multiplier_decay_timer >= 0.5:
            self.multiplier_decay_timer = 0
            self.multiplier = max(1.0, self.multiplier - 0.5)

        any_graze = False
        for enemy in self.enemies[:]:
            enemy.update(dt, self.player.x, self.player.y, time_scale)

            if self.check_graze(enemy):
                any_graze = True
                if random.random() < 0.3:
                    self.graze_sparks.append(
                        GrazeSpark(enemy.x, enemy.y, self.player.x, self.player.y)
                    )

            if enemy.enemy_type == "scanner":
                if enemy.check_collision(
                    self.player.x, self.player.y, self.player.size
                ):
                    if not self.player.is_dashing and self.player.take_damage(20):
                        self.trigger_shake(15, 0.3)
                        self.hitstop_frames = 5
            elif enemy.enemy_type == "node":
                if enemy.check_collision(
                    self.player.x, self.player.y, self.player.size
                ):
                    if self.player.take_damage(15):
                        self.spawn_particles(self.player.x, self.player.y, ENEMY_RED)
                        self.trigger_shake(12, 0.25)
                        self.hitstop_frames = 5
            else:
                collision_dist = enemy.get_collision_radius() + self.player.size * 0.5
                if (
                    distance(enemy.x, enemy.y, self.player.x, self.player.y)
                    < collision_dist
                ):
                    if self.player.take_damage(15):
                        self.spawn_particles(enemy.x, enemy.y, ENEMY_RED)
                        self.add_grid_distortion(enemy.x, enemy.y, 20)
                        self.trigger_shake(12, 0.25)
                        self.hitstop_frames = 5
                        self.enemies.remove(enemy)

            if not enemy.alive:
                self.enemies.remove(enemy)

        if any_graze:
            self.multiplier = min(8.0, self.multiplier + dt * 2)
            self.multiplier_decay_timer = 0

        for spark in self.graze_sparks[:]:
            spark.update(dt, self.player.x, self.player.y)
            if spark.life <= 0:
                self.graze_sparks.remove(spark)

        for line in self.implosion_lines[:]:
            line.update(dt)
            if line.life <= 0:
                self.implosion_lines.remove(line)

        for prism in self.prisms[:]:
            prism.update(dt, time_scale)
            if (
                distance(prism.x, prism.y, self.player.x, self.player.y)
                < prism.size + self.player.size * 0.5
            ):
                self.player.health = min(
                    self.player.max_health, self.player.health + 20
                )
                self.spawn_implosion(self.player.x, self.player.y, PICKUP_GREEN)
                self.trigger_flash(PICKUP_GREEN, 0.05)
                self.score += int(100 * self.multiplier)
                self.prisms.remove(prism)

        for powerup in self.powerups[:]:
            powerup.update(dt, time_scale)
            if (
                distance(powerup.x, powerup.y, self.player.x, self.player.y)
                < powerup.size + self.player.size * 0.5
            ):
                if powerup.power_type == PowerUpType.DATA_PURGE:
                    self.trigger_data_purge()
                else:
                    self.time_dilation_timer = 5.0
                    self.spawn_implosion(self.player.x, self.player.y, PLAYER_CYAN)
                    self.trigger_flash(PLAYER_CYAN, 0.05)
                self.powerups.remove(powerup)

        for particle in self.particles[:]:
            particle.update(dt, time_scale)
            if particle.life <= 0:
                self.particles.remove(particle)

        if self.player.health <= 0:
            for _ in range(30):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(50, 200)
                self.death_particles.append(
                    Particle(
                        x=self.player.x,
                        y=self.player.y,
                        vx=math.cos(angle) * speed,
                        vy=math.sin(angle) * speed + 50,
                        life=1.5,
                        max_life=1.5,
                        size=random.uniform(3, 10),
                        color=PLAYER_WHITE,
                        shape="hollow",
                    )
                )
            self.state = "gameover"

    def draw_hud(self):
        health_ratio = self.player.health / self.player.max_health
        bar_width = 200
        bar_height = 12
        bar_x = WIDTH // 2 - bar_width // 2
        bar_y = 15
        segment_count = 10
        segment_width = bar_width // segment_count - 2

        for i in range(segment_count):
            sx = bar_x + i * (segment_width + 2)
            filled = i < int(health_ratio * segment_count)

            points = [
                (sx + 4, bar_y),
                (sx + segment_width, bar_y),
                (sx + segment_width - 4, bar_y + bar_height),
                (sx, bar_y + bar_height),
            ]

            if filled:
                color = PLAYER_CYAN if health_ratio > 0.3 else UI_CRITICAL
                pygame.draw.polygon(self.screen, color, points)
            pygame.draw.polygon(self.screen, GRID_DARK, points, 1)

        label = self.font_tiny.render("SYSTEM INTEGRITY", True, TEXT_WHITE)
        label_rect = label.get_rect(centerx=WIDTH // 2, top=bar_y + bar_height + 4)
        self.screen.blit(label, label_rect)

        score_str = f"{self.score:06d}"
        score_text = self.font_small.render(score_str, True, POWERUP_YELLOW)
        self.screen.blit(score_text, (15, 15))

        mult_str = f"x{self.multiplier:.1f}"
        if self.multiplier >= 8:
            mult_color = UI_CRITICAL
            offset = (random.uniform(-3, 3), random.uniform(-3, 3))
        elif self.multiplier >= 4:
            mult_color = PLAYER_CYAN
            offset = (0, 0)
        else:
            mult_color = POWERUP_YELLOW
            offset = (0, 0)

        mult_text = self.font_multiplier.render(mult_str, True, mult_color)
        mult_rect = mult_text.get_rect(right=WIDTH - 15 + offset[0], top=15 + offset[1])
        self.screen.blit(mult_text, mult_rect)

        wave = WAVES[self.current_wave]
        wave_text = self.font_tiny.render(
            f"WAVE {self.current_wave + 1}: {wave.name}", True, INACTIVE_GREY
        )
        self.screen.blit(wave_text, (15, HEIGHT - 25))

        if self.time_dilation_timer > 0:
            dilation_text = self.font_small.render(
                f"TIME DILATION: {self.time_dilation_timer:.1f}s", True, PLAYER_CYAN
            )
            dilation_rect = dilation_text.get_rect(
                centerx=WIDTH // 2, bottom=HEIGHT - 15
            )
            self.screen.blit(dilation_text, dilation_rect)

    def draw_game(self):
        game_surface = pygame.Surface((WIDTH, HEIGHT))
        offset = self.get_shake_offset()
        desat = self.get_desaturation()

        game_surface.fill(VOID_BLACK)

        for dust in self.dust_particles:
            dust.draw(game_surface, offset)

        self.draw_grid(game_surface, offset)

        score_bg = self.font_score_bg.render(str(self.score), True, (255, 255, 255))
        score_bg.set_alpha(10)
        score_rect = score_bg.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        game_surface.blit(score_bg, score_rect)

        for particle in self.particles:
            particle.draw(game_surface, offset)

        for spark in self.graze_sparks:
            spark.draw(game_surface, offset)

        for line in self.implosion_lines:
            line.draw(game_surface, self.player.x, self.player.y, offset)

        for prism in self.prisms:
            prism.draw(game_surface, offset, desat)

        for powerup in self.powerups:
            powerup.draw(game_surface, offset, desat)

        for enemy in self.enemies:
            enemy.draw(game_surface, offset, desat)

        self.player.draw(game_surface, offset)

        self.draw_vignette(game_surface)
        self.draw_scanlines_overlay(game_surface)
        self.draw_noise(game_surface)

        if self.flash_timer > 0:
            flash_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            alpha = int(150 * (self.flash_timer / 0.1))
            flash_surf.fill((*self.flash_color, min(255, alpha)))
            game_surface.blit(flash_surf, (0, 0))

        if abs(self.shake_rotation) > 0.1:
            rotated = pygame.transform.rotate(game_surface, self.shake_rotation)
            rot_rect = rotated.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            self.screen.fill(VOID_BLACK)
            self.screen.blit(rotated, rot_rect)
            self.shake_rotation *= 0.9
        else:
            self.screen.blit(game_surface, (0, 0))

        self.draw_hud()

        if self.wave_transition:
            next_wave = (self.current_wave + 1) % len(WAVES)
            next_wave_name = WAVES[next_wave].name
            text = (
                f"CYCLE {self.cycle + 1} INCOMING"
                if self.current_wave + 1 >= len(WAVES)
                else f"NEXT: {next_wave_name}"
            )
            wave_text = self.font_medium.render(text, True, PLAYER_CYAN)
            wave_rect = wave_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
            self.screen.blit(wave_text, wave_rect)

    def draw_menu(self):
        self.menu_time += 1 / 60
        self.screen.fill(VOID_BLACK)

        for dust in self.dust_particles:
            dust.update(1 / 60)
            dust.draw(self.screen, (0, 0))

        for i in range(15):
            x = 550 + math.sin(self.menu_time + i * 0.5) * 80
            y = 300 + math.cos(self.menu_time * 0.7 + i * 0.3) * 120
            size = 20 + math.sin(self.menu_time * 2 + i) * 5
            pygame.draw.rect(
                self.screen,
                ENEMY_RED,
                (int(x - size / 2), int(y - size / 2), int(size), int(size)),
                1,
            )

        glitch_offset = random.randint(-2, 2) if random.random() < 0.05 else 0

        title1_r = self.font_large.render("CHROMATIC", True, ENEMY_RED)
        title1_c = self.font_large.render("CHROMATIC", True, PLAYER_CYAN)
        title1 = self.font_large.render("CHROMATIC", True, PLAYER_WHITE)
        self.screen.blit(title1_r, (48 + glitch_offset, 98))
        self.screen.blit(title1_c, (52 - glitch_offset, 102))
        self.screen.blit(title1, (50, 100))

        title2_r = self.font_large.render("DECAY", True, ENEMY_RED)
        title2_c = self.font_large.render("DECAY", True, PLAYER_CYAN)
        title2 = self.font_large.render("DECAY", True, PLAYER_WHITE)
        self.screen.blit(title2_r, (48 - glitch_offset, 178))
        self.screen.blit(title2_c, (52 + glitch_offset, 182))
        self.screen.blit(title2, (50, 180))

        version = self.font_tiny.render(
            "v3.0 // SYSTEM FAILURE EDITION", True, INACTIVE_GREY
        )
        self.screen.blit(version, (50, 260))

        options = ["> INITIATE <", "  ABORT    "]
        for i, opt in enumerate(options):
            color = PLAYER_CYAN if i == 0 else TEXT_WHITE
            text = self.font_small.render(opt, True, color)
            self.screen.blit(text, (50, 400 + i * 45))

        controls = [
            "WASD/ARROWS: Navigate",
            "SPACE: Phase Dash",
            "Graze enemies for multiplier",
        ]
        for i, ctrl in enumerate(controls):
            text = self.font_tiny.render(ctrl, True, INACTIVE_GREY)
            self.screen.blit(text, (50, HEIGHT - 90 + i * 20))

        hint = self.font_small.render("ENTER to start | ESC to quit", True, PLAYER_CYAN)
        self.screen.blit(hint, (50, HEIGHT - 35))

        self.screen.blit(self.vignette, (0, 0))
        self.screen.blit(self.scanlines, (0, 0))

    def draw_pause(self):
        self.draw_game()

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        for y in range(0, HEIGHT, 2):
            pygame.draw.line(self.screen, (0, 0, 0), (0, y), (WIDTH, y))

        box_rect = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2 - 100, 400, 200)
        pygame.draw.rect(self.screen, VOID_BLACK, box_rect)
        pygame.draw.rect(self.screen, PLAYER_WHITE, box_rect, 2)

        if int(pygame.time.get_ticks() / 500) % 2 == 0:
            text = self.font_medium.render("SYSTEM HALTED", True, PLAYER_WHITE)
            text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20))
            self.screen.blit(text, text_rect)

        resume = self.font_small.render("ESC to resume", True, TEXT_WHITE)
        resume_rect = resume.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40))
        self.screen.blit(resume, resume_rect)

    def draw_gameover(self):
        self.screen.fill((15, 5, 5))

        for particle in self.death_particles:
            particle.update(1 / 60, 1.0)
            particle.vy += 80 * (1 / 60)
            particle.draw(self.screen, (0, 0))

        for _ in range(15):
            x, y = random.randint(0, WIDTH), random.randint(0, HEIGHT)
            w, h = random.randint(20, 80), random.randint(20, 80)
            pygame.draw.rect(self.screen, ENEMY_DARK, (x, y, w, h), 1)

        title = self.font_large.render("SIGNAL LOST", True, ENEMY_RED)
        title_rect = title.get_rect(center=(WIDTH // 2, 100))
        self.screen.blit(title, title_rect)

        stats = [
            f"FINAL SCORE: {self.score}",
            f"TIME: {int(self.time_survived)}s",
            f"WAVE: {self.current_wave + 1}",
            f"CYCLES: {self.cycle}",
        ]
        for i, stat in enumerate(stats):
            text = self.font_small.render(stat, True, TEXT_WHITE)
            text_rect = text.get_rect(center=(WIDTH // 2, 200 + i * 40))
            self.screen.blit(text, text_rect)

        reboot = self.font_medium.render("[ R ] REBOOT", True, PLAYER_CYAN)
        reboot_rect = reboot.get_rect(center=(WIDTH // 2, 420))
        self.screen.blit(reboot, reboot_rect)

        exit_text = self.font_small.render("ESC to exit", True, INACTIVE_GREY)
        exit_rect = exit_text.get_rect(center=(WIDTH // 2, 470))
        self.screen.blit(exit_text, exit_rect)

        self.screen.blit(self.vignette, (0, 0))
        self.screen.blit(self.scanlines, (0, 0))

    def handle_dash(self):
        if self.player.dash():
            self.spawn_particles(self.player.x, self.player.y, PLAYER_CYAN, 15)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if self.state == "menu":
                        if event.key == pygame.K_RETURN:
                            self.reset_game()
                            self.state = "playing"
                        elif event.key == pygame.K_ESCAPE:
                            running = False
                    elif self.state == "playing":
                        if event.key == pygame.K_ESCAPE:
                            self.state = "paused"
                        elif event.key == pygame.K_SPACE:
                            self.handle_dash()
                    elif self.state == "paused":
                        if event.key == pygame.K_ESCAPE:
                            self.state = "playing"
                    elif self.state == "gameover":
                        if event.key == pygame.K_r:
                            self.reset_game()
                            self.state = "playing"
                        elif event.key == pygame.K_ESCAPE:
                            self.state = "menu"
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 3 and self.state == "playing":
                        self.handle_dash()

            if self.state == "menu":
                self.draw_menu()
            elif self.state == "playing":
                self.update_game(dt)
                self.draw_game()
            elif self.state == "paused":
                self.draw_pause()
            elif self.state == "gameover":
                self.draw_gameover()

            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()
