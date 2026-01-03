"""
CHROMATIC DECAY v2.0 - Abstract survival bullet hell where health = color saturation.
"""

import pygame
import random
import math
import sys
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum

pygame.init()

WIDTH, HEIGHT = 800, 600
FPS = 60

VOID_BLACK = (5, 5, 5)
GRID_GREY = (26, 26, 26)
PLAYER_WHITE = (255, 255, 255)
ENEMY_RED = (255, 0, 60)
PRISM_CYAN = (0, 240, 255)
SCORE_YELLOW = (255, 230, 0)
TEXT_WHITE = (224, 224, 224)
INACTIVE_GREY = (64, 64, 64)

Color = Tuple[int, int, int]


class PowerUpType(Enum):
    DATA_PURGE = 1
    TIME_DILATION = 2


def lerp_color(color1: Color, color2: Color, t: float) -> Color:
    t = max(0, min(1, t))
    r = int(color1[0] + (color2[0] - color1[0]) * t)
    g = int(color1[1] + (color2[1] - color1[1]) * t)
    b = int(color1[2] + (color2[2] - color1[2]) * t)
    return (r, g, b)


def desaturate(color: Color, amount: float) -> Color:
    grey = int(sum(color) / 3)
    return lerp_color(color, (grey, grey, grey), amount)


def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


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

    def update(self, dt: float, time_scale: float = 1.0):
        self.x += self.vx * dt * time_scale
        self.y += self.vy * dt * time_scale
        self.vx *= 0.95
        self.vy *= 0.95
        self.life -= dt

    def draw(self, surface: pygame.Surface, offset: Tuple[float, float]):
        if self.life <= 0:
            return
        alpha = self.life / self.max_life
        r = min(255, self.color[0] + int((1 - alpha) * 50))
        g = min(255, self.color[1] + int((1 - alpha) * 100))
        b = self.color[2]
        color = (r, g, b)
        size = int(self.size * alpha)
        if size > 0:
            px, py = int(self.x + offset[0]), int(self.y + offset[1])
            if self.shape == "triangle":
                points = [
                    (px, py - size),
                    (px - size, py + size),
                    (px + size, py + size),
                ]
                pygame.draw.polygon(surface, color, points)
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
        self.x = self.x + (self.target_x - self.x) * t * 0.3
        self.y = self.y + (self.target_y - self.y) * t * 0.3
        self.life -= dt

    def draw(self, surface: pygame.Surface, offset: Tuple[float, float]):
        if self.life <= 0:
            return
        alpha = self.life / 0.3
        size = int(3 * alpha)
        if size > 0:
            pygame.draw.rect(
                surface,
                SCORE_YELLOW,
                (int(self.x + offset[0]), int(self.y + offset[1]), size, size),
            )


class Player:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.size = 20
        self.speed = 600
        self.friction = 0.92
        self.health = 100
        self.max_health = 100
        self.rotation = 0
        self.trail: List[Tuple[float, float, float]] = []
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
        self.ghost_positions: List[Tuple[float, float, float]] = []
        self.last_move_x = 1.0
        self.last_move_y = 0.0

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
                self.dash_dir_x = 1
                self.dash_dir_y = 0
            self.ghost_positions = [
                (self.x, self.y, self.rotation),
                (
                    self.x + self.dash_dir_x * self.dash_distance * 0.5,
                    self.y + self.dash_dir_y * self.dash_distance * 0.5,
                    self.rotation,
                ),
            ]
            self.chromatic_timer = 0.1
            return True
        return False

    def update(self, dt: float, keys, time_scale: float = 1.0):
        if self.dash_cooldown > 0:
            self.dash_cooldown -= dt

        if self.is_dashing:
            self.dash_timer -= dt
            dash_speed = self.dash_distance / self.dash_duration
            self.x += self.dash_dir_x * dash_speed * dt
            self.y += self.dash_dir_y * dash_speed * dt
            if self.dash_timer <= 0:
                self.is_dashing = False
                self.ghost_positions.append((self.x, self.y, self.rotation))
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
                self.last_move_x = ax
                self.last_move_y = ay

            self.vx += ax * dt * time_scale
            self.vy += ay * dt * time_scale
            self.vx *= self.friction
            self.vy *= self.friction
            self.x += self.vx * dt * time_scale
            self.y += self.vy * dt * time_scale

        self.x = max(self.size, min(WIDTH - self.size, self.x))
        self.y = max(self.size, min(HEIGHT - self.size, self.y))

        if abs(self.vx) > 1 or abs(self.vy) > 1 or self.is_dashing:
            self.rotation += 200 * dt

        self.trail.append((self.x, self.y, self.rotation))
        if len(self.trail) > 4:
            self.trail.pop(0)

        if self.invincible_timer > 0:
            self.invincible_timer -= dt
        if self.chromatic_timer > 0:
            self.chromatic_timer -= dt

        for i, (gx, gy, gr) in enumerate(self.ghost_positions):
            self.ghost_positions[i] = (gx, gy, gr)
        if len(self.ghost_positions) > 0:
            self.ghost_positions = [(gx, gy, gr) for gx, gy, gr in self.ghost_positions]
            if self.dash_timer <= -0.3:
                self.ghost_positions = []

    def take_damage(self, amount: int) -> bool:
        if self.invincible_timer <= 0 and not self.is_dashing:
            self.health -= amount
            self.invincible_timer = 0.5
            self.chromatic_timer = 0.15
            return True
        return False

    def draw(self, surface: pygame.Surface, offset: Tuple[float, float]):
        for gx, gy, gr in self.ghost_positions:
            ghost_color = (0, 120, 128)
            self._draw_rotated_rect(
                surface, gx + offset[0], gy + offset[1], self.size, gr, ghost_color
            )

        for i, (tx, ty, tr) in enumerate(self.trail[:-1]):
            alpha = (i + 1) / len(self.trail) * 0.5
            trail_color = (int(255 * alpha), int(255 * alpha), int(255 * alpha))
            self._draw_rotated_rect(
                surface, tx + offset[0], ty + offset[1], self.size, tr, trail_color
            )

        if self.chromatic_timer > 0:
            self._draw_rotated_rect(
                surface,
                self.x + offset[0] - 2,
                self.y + offset[1] - 2,
                self.size,
                self.rotation,
                ENEMY_RED,
            )
            self._draw_rotated_rect(
                surface,
                self.x + offset[0] + 2,
                self.y + offset[1] + 2,
                self.size,
                self.rotation,
                PRISM_CYAN,
            )

        if self.invincible_timer <= 0 or int(self.invincible_timer * 10) % 2 == 0:
            self._draw_rotated_rect(
                surface,
                self.x + offset[0],
                self.y + offset[1],
                self.size,
                self.rotation,
                PLAYER_WHITE,
            )

        self._draw_dash_indicator(surface, offset)

    def _draw_dash_indicator(
        self, surface: pygame.Surface, offset: Tuple[float, float]
    ):
        dash_ready = self.dash_cooldown <= 0
        indicator_size = self.size + 8
        px, py = self.x + offset[0], self.y + offset[1]

        if dash_ready:
            color = PLAYER_WHITE
            for angle in [45, 135, 225, 315]:
                rad = math.radians(angle + self.rotation)
                x1 = px + math.cos(rad) * indicator_size * 0.7
                y1 = py + math.sin(rad) * indicator_size * 0.7
                rad2 = math.radians(angle + 90 + self.rotation)
                x2 = px + math.cos(rad2) * indicator_size * 0.7
                y2 = py + math.sin(rad2) * indicator_size * 0.7
                pygame.draw.line(surface, color, (x1, y1), (x2, y2), 1)
        else:
            progress = 1 - (self.dash_cooldown / self.dash_cooldown_max)
            segments = 4
            for i in range(int(segments * progress)):
                angle = 45 + i * 90
                rad = math.radians(angle + self.rotation)
                x1 = px + math.cos(rad) * indicator_size * 0.7
                y1 = py + math.sin(rad) * indicator_size * 0.7
                rad2 = math.radians(angle + 90 + self.rotation)
                x2 = px + math.cos(rad2) * indicator_size * 0.7
                y2 = py + math.sin(rad2) * indicator_size * 0.7
                pygame.draw.line(surface, INACTIVE_GREY, (x1, y1), (x2, y2), 1)

    def _draw_rotated_rect(
        self,
        surface: pygame.Surface,
        x: float,
        y: float,
        size: int,
        rotation: float,
        color: Color,
    ):
        points = []
        for angle in [45, 135, 225, 315]:
            rad = math.radians(angle + rotation)
            px = x + math.cos(rad) * size * 0.7
            py = y + math.sin(rad) * size * 0.7
            points.append((px, py))
        pygame.draw.polygon(surface, color, points)


class StaticEater:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.speed = random.uniform(50, 90)
        self.jitter_parts: List[Tuple[float, float]] = [
            (random.uniform(-8, 8), random.uniform(-8, 8)) for _ in range(8)
        ]
        self.alive = True
        self.size = 15
        self.enemy_type = "static_eater"

    def update(
        self, dt: float, player_x: float, player_y: float, time_scale: float = 1.0
    ):
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0:
            self.x += (dx / dist) * self.speed * dt * time_scale
            self.y += (dy / dist) * self.speed * dt * time_scale

        for i in range(len(self.jitter_parts)):
            jx, jy = self.jitter_parts[i]
            jx += random.uniform(-2, 2)
            jy += random.uniform(-2, 2)
            jx = max(-10, min(10, jx))
            jy = max(-10, min(10, jy))
            self.jitter_parts[i] = (jx, jy)

    def draw(
        self, surface: pygame.Surface, offset: Tuple[float, float], desaturation: float
    ):
        color = desaturate(ENEMY_RED, desaturation)
        for jx, jy in self.jitter_parts:
            pygame.draw.rect(
                surface,
                color,
                (
                    int(self.x + jx + offset[0]) - 2,
                    int(self.y + jy + offset[1]) - 2,
                    4,
                    4,
                ),
            )

    def get_collision_radius(self) -> float:
        return self.size


class Vectro:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 160
        self.turn_rate = 1.5
        self.size = 18
        self.alive = True
        self.enemy_type = "vectro"
        self.angle = random.uniform(0, 360)
        self.charge_timer = 0.0
        self.is_charging = False
        self.target_x = 0.0
        self.target_y = 0.0
        self.trail: List[Tuple[float, float]] = []

    def update(
        self, dt: float, player_x: float, player_y: float, time_scale: float = 1.0
    ):
        self.charge_timer += dt * time_scale

        if self.charge_timer >= 1.5:
            self.charge_timer = 0
            self.is_charging = True
            self.target_x = player_x
            self.target_y = player_y
            dx = self.target_x - self.x
            dy = self.target_y - self.y
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
            dx = player_x - self.x
            dy = player_y - self.y
            target_angle = math.degrees(math.atan2(dy, dx))
            angle_diff = (target_angle - self.angle + 180) % 360 - 180
            self.angle += angle_diff * self.turn_rate * dt * time_scale
            self.x += (
                math.cos(math.radians(self.angle)) * self.speed * 0.5 * dt * time_scale
            )
            self.y += (
                math.sin(math.radians(self.angle)) * self.speed * 0.5 * dt * time_scale
            )

        self.trail.append((self.x, self.y))
        if len(self.trail) > 10:
            self.trail.pop(0)

    def draw(
        self, surface: pygame.Surface, offset: Tuple[float, float], desaturation: float
    ):
        color = desaturate(ENEMY_RED, desaturation)

        for i, (tx, ty) in enumerate(self.trail[:-1]):
            alpha = (i + 1) / len(self.trail) * 0.3
            trail_color = lerp_color(VOID_BLACK, color, alpha)
            pygame.draw.line(
                surface,
                trail_color,
                (int(tx + offset[0]), int(ty + offset[1])),
                (
                    int(self.trail[i + 1][0] + offset[0]),
                    int(self.trail[i + 1][1] + offset[1]),
                ),
                2,
            )

        rad = math.radians(self.angle)
        tip_x = self.x + math.cos(rad) * self.size
        tip_y = self.y + math.sin(rad) * self.size
        left_x = self.x + math.cos(rad + 2.5) * self.size * 0.7
        left_y = self.y + math.sin(rad + 2.5) * self.size * 0.7
        right_x = self.x + math.cos(rad - 2.5) * self.size * 0.7
        right_y = self.y + math.sin(rad - 2.5) * self.size * 0.7

        points = [
            (tip_x + offset[0], tip_y + offset[1]),
            (left_x + offset[0], left_y + offset[1]),
            (right_x + offset[0], right_y + offset[1]),
        ]
        pygame.draw.polygon(surface, color, points, 2)

    def get_collision_radius(self) -> float:
        return self.size * 0.8


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

        if horizontal:
            self.x = 0
            self.y = -50
            self.width = WIDTH
            self.height = self.size
            self.warning_y = -10
        else:
            self.x = -50
            self.y = 0
            self.width = self.size
            self.height = HEIGHT
            self.warning_x = -10

    def update(
        self, dt: float, player_x: float, player_y: float, time_scale: float = 1.0
    ):
        self.flicker_timer += dt * 10

        if self.is_warning:
            self.warning_timer -= dt
            if self.warning_timer <= 0:
                self.is_warning = False
                if self.horizontal:
                    self.y = 0
                else:
                    self.x = 0
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
                    pygame.draw.line(surface, color, (0, 0), (WIDTH, 0), 2)
                else:
                    pygame.draw.line(surface, color, (0, 0), (0, HEIGHT), 2)
        else:
            flicker_offset = math.sin(self.flicker_timer) * 3
            if self.horizontal:
                h = self.height + flicker_offset
                rect = pygame.Rect(
                    self.x + offset[0], self.y + offset[1], self.width, h
                )
            else:
                w = self.width + flicker_offset
                rect = pygame.Rect(
                    self.x + offset[0], self.y + offset[1], w, self.height
                )

            s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            s.fill((*color, 150))
            surface.blit(s, rect.topleft)

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
        else:
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
        self.size = 25
        self.alive = True
        self.enemy_type = "node"
        self.rotation = 0
        self.pulse_timer = 0.0
        self.pulse_interval = 2.0
        self.shockwave_radius = 0.0
        self.shockwave_active = False
        self.shockwave_max = 150
        self.shockwave_speed = 400
        self.vertex_offsets = [random.uniform(-3, 3) for _ in range(6)]

    def update(
        self, dt: float, player_x: float, player_y: float, time_scale: float = 1.0
    ):
        self.rotation += 30 * dt * time_scale
        self.pulse_timer += dt * time_scale

        for i in range(len(self.vertex_offsets)):
            self.vertex_offsets[i] += random.uniform(-1, 1) * dt * 10
            self.vertex_offsets[i] = max(-5, min(5, self.vertex_offsets[i]))

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

        if self.shockwave_active:
            pygame.draw.circle(
                surface,
                color,
                (int(self.x + offset[0]), int(self.y + offset[1])),
                int(self.shockwave_radius),
                2,
            )

        points = []
        for i in range(6):
            angle = math.radians(self.rotation + i * 60)
            dist = self.size + self.vertex_offsets[i]
            px = self.x + offset[0] + math.cos(angle) * dist
            py = self.y + offset[1] + math.sin(angle) * dist
            points.append((px, py))
        pygame.draw.polygon(surface, color, points, 2)

    def check_collision(
        self, player_x: float, player_y: float, player_size: float
    ) -> bool:
        dist = distance(self.x, self.y, player_x, player_y)
        if dist < self.size + player_size / 2:
            return True
        if self.shockwave_active:
            ring_inner = self.shockwave_radius - 10
            ring_outer = self.shockwave_radius + 10
            if ring_inner < dist < ring_outer:
                return True
        return False

    def get_collision_radius(self) -> float:
        return self.size


class Prism:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.rotation = random.uniform(0, 360)
        self.pulse_timer = random.uniform(0, math.pi * 2)
        self.size = 15
        self.alive = True

    def update(self, dt: float, time_scale: float = 1.0):
        self.rotation += 100 * dt * time_scale
        self.pulse_timer += dt * 4

    def draw(
        self, surface: pygame.Surface, offset: Tuple[float, float], desaturation: float
    ):
        color = desaturate(PRISM_CYAN, desaturation)
        scale = 1.0 + math.sin(self.pulse_timer) * 0.2
        size = self.size * scale

        points = []
        for i in range(3):
            angle = math.radians(self.rotation + i * 120)
            px = self.x + offset[0] + math.cos(angle) * size
            py = self.y + offset[1] + math.sin(angle) * size
            points.append((px, py))
        pygame.draw.polygon(surface, color, points)
        pygame.draw.polygon(surface, PLAYER_WHITE, points, 2)


class PowerUp:
    def __init__(self, x: float, y: float, power_type: PowerUpType):
        self.x = x
        self.y = y
        self.power_type = power_type
        self.rotation = 0
        self.pulse_timer = 0
        self.size = 18
        self.alive = True

    def update(self, dt: float, time_scale: float = 1.0):
        self.rotation += 80 * dt * time_scale
        self.pulse_timer += dt * 3

    def draw(
        self, surface: pygame.Surface, offset: Tuple[float, float], desaturation: float
    ):
        scale = 1.0 + math.sin(self.pulse_timer) * 0.15
        size = self.size * scale
        px, py = self.x + offset[0], self.y + offset[1]

        if self.power_type == PowerUpType.DATA_PURGE:
            color = desaturate(SCORE_YELLOW, desaturation)
            points = [
                (px, py - size),
                (px + size, py),
                (px, py + size),
                (px - size, py),
            ]
            pygame.draw.polygon(surface, color, points)
            pygame.draw.polygon(surface, PLAYER_WHITE, points, 2)
        else:
            color = desaturate(PRISM_CYAN, desaturation)
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
            pygame.draw.polygon(
                surface,
                PLAYER_WHITE,
                [
                    (px, py - tri_size),
                    (px - tri_size * 0.7, py),
                    (px + tri_size * 0.7, py),
                ],
                1,
            )
            pygame.draw.polygon(
                surface,
                PLAYER_WHITE,
                [
                    (px, py + tri_size),
                    (px - tri_size * 0.7, py),
                    (px + tri_size * 0.7, py),
                ],
                1,
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
        self.font_score = pygame.font.SysFont("Consolas", 200, bold=True)
        self.font_multiplier = pygame.font.SysFont("Consolas", 32, bold=True)
        self.state = "menu"
        self.reset_game()

    def reset_game(self):
        self.player = Player(WIDTH // 2, HEIGHT // 2)
        self.enemies: List = []
        self.prisms: List[Prism] = []
        self.powerups: List[PowerUp] = []
        self.particles: List[Particle] = []
        self.graze_sparks: List[GrazeSpark] = []
        self.score = 0
        self.time_survived = 0
        self.spawn_timer = 0
        self.prism_spawn_timer = 0
        self.powerup_spawn_timer = 0
        self.screen_shake = 0
        self.shake_intensity = 0
        self.beat_timer = 0
        self.hitstop_frames = 0
        self.time_dilation_timer = 0
        self.invert_timer = 0
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
        x = random.randint(50, WIDTH - 50)
        y = random.randint(50, HEIGHT - 50)
        self.prisms.append(Prism(x, y))

    def spawn_powerup(self):
        x = random.randint(80, WIDTH - 80)
        y = random.randint(80, HEIGHT - 80)
        power_type = random.choice([PowerUpType.DATA_PURGE, PowerUpType.TIME_DILATION])
        self.powerups.append(PowerUp(x, y, power_type))

    def spawn_particles(
        self, x: float, y: float, color: Color, count: int = 20, shape: str = "rect"
    ):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(100, 300)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed,
                    life=0.5,
                    max_life=0.5,
                    size=random.uniform(2, 5),
                    color=color,
                    shape=shape,
                )
            )

    def trigger_data_purge(self):
        self.spawn_particles(self.player.x, self.player.y, PLAYER_WHITE, 50)
        self.invert_timer = 0.5
        self.trigger_shake(15, 0.3)

        for enemy in self.enemies[:]:
            if enemy.enemy_type in ["static_eater", "vectro"]:
                self.spawn_particles(enemy.x, enemy.y, ENEMY_RED, 10)
                self.score += 50 * int(self.multiplier)
                self.enemies.remove(enemy)
            elif enemy.enemy_type == "node":
                dx = enemy.x - self.player.x
                dy = enemy.y - self.player.y
                dist = max(1, distance(enemy.x, enemy.y, self.player.x, self.player.y))
                push_force = 200
                enemy.x += (dx / dist) * push_force
                enemy.y += (dy / dist) * push_force

    def trigger_shake(self, intensity: float, duration: float):
        self.shake_intensity = max(self.shake_intensity, intensity)
        self.screen_shake = max(self.screen_shake, duration)

    def get_shake_offset(self) -> Tuple[float, float]:
        if self.screen_shake <= 0:
            return (0, 0)
        return (
            random.uniform(-self.shake_intensity, self.shake_intensity),
            random.uniform(-self.shake_intensity, self.shake_intensity),
        )

    def get_desaturation(self) -> float:
        return 1.0 - (self.player.health / self.player.max_health)

    def get_grid_color(self) -> Color:
        health_ratio = self.player.health / self.player.max_health
        if health_ratio > 0.5:
            return lerp_color(INACTIVE_GREY, PRISM_CYAN, (health_ratio - 0.5) * 2)
        elif health_ratio > 0.1:
            return lerp_color(ENEMY_RED, INACTIVE_GREY, (health_ratio - 0.1) / 0.4)
        else:
            return ENEMY_RED

    def draw_grid(self, surface: pygame.Surface, offset: Tuple[float, float]):
        color = self.get_grid_color()
        desat = self.get_desaturation()
        color = desaturate(color, desat * 0.5)
        pulse = 1.0 + math.sin(self.beat_timer * math.pi * 2) * 0.3

        if self.player.health <= 10 and random.random() < 0.3:
            return

        grid_size = 40
        line_width = max(1, int(pulse))

        wave_offset = 0
        if self.time_dilation_timer > 0:
            wave_offset = math.sin(self.time_survived * 3) * 5

        for x in range(0, WIDTH + grid_size, grid_size):
            wo = math.sin((x + self.time_survived * 50) * 0.05) * wave_offset
            pygame.draw.line(
                surface,
                color,
                (x + offset[0] + wo, offset[1]),
                (x + offset[0] + wo, HEIGHT + offset[1]),
                line_width,
            )
        for y in range(0, HEIGHT + grid_size, grid_size):
            wo = math.sin((y + self.time_survived * 50) * 0.05) * wave_offset
            pygame.draw.line(
                surface,
                color,
                (offset[0], y + offset[1] + wo),
                (WIDTH + offset[0], y + offset[1] + wo),
                line_width,
            )

    def draw_scanlines(self, surface: pygame.Surface):
        for y in range(0, HEIGHT, 4):
            pygame.draw.line(surface, (0, 0, 0), (0, y), (WIDTH, y))

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
        if self.invert_timer > 0:
            self.invert_timer -= dt

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
                x = random.randint(100, WIDTH - 100)
                y = random.randint(100, HEIGHT - 100)
                self.enemies.append(Node(x, y))
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
            self.shake_intensity *= 0.9

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
                    if not self.player.is_dashing:
                        if self.player.take_damage(20):
                            self.trigger_shake(12, 0.3)
                            self.hitstop_frames = 5
            elif enemy.enemy_type == "node":
                if enemy.check_collision(
                    self.player.x, self.player.y, self.player.size
                ):
                    if self.player.take_damage(15):
                        self.spawn_particles(self.player.x, self.player.y, ENEMY_RED)
                        self.trigger_shake(10, 0.25)
                        self.hitstop_frames = 5
            else:
                collision_dist = enemy.get_collision_radius() + self.player.size * 0.5
                if (
                    distance(enemy.x, enemy.y, self.player.x, self.player.y)
                    < collision_dist
                ):
                    if self.player.take_damage(15):
                        self.spawn_particles(enemy.x, enemy.y, ENEMY_RED)
                        self.trigger_shake(10, 0.25)
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

        for prism in self.prisms[:]:
            prism.update(dt, time_scale)
            if (
                distance(prism.x, prism.y, self.player.x, self.player.y)
                < prism.size + self.player.size * 0.5
            ):
                self.player.health = min(
                    self.player.max_health, self.player.health + 20
                )
                self.spawn_particles(prism.x, prism.y, PRISM_CYAN, 15)
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
                    self.spawn_particles(powerup.x, powerup.y, PRISM_CYAN, 20)
                self.powerups.remove(powerup)

        for particle in self.particles[:]:
            particle.update(dt, time_scale)
            if particle.life <= 0:
                self.particles.remove(particle)

        if self.player.health <= 0:
            for _ in range(25):
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
                        size=random.uniform(3, 8),
                        color=PLAYER_WHITE,
                        shape="triangle",
                    )
                )
            self.state = "gameover"

    def draw_hud(self):
        health_ratio = self.player.health / self.player.max_health
        bar_chars = int(health_ratio * 10)
        bar_str = "|" * bar_chars + " " * (10 - bar_chars)

        if health_ratio > 0.5:
            bar_color = PRISM_CYAN
        elif health_ratio > 0.25:
            bar_color = SCORE_YELLOW
        else:
            bar_color = ENEMY_RED

        integrity_text = self.font_small.render(
            f"INTEGRITY: [{bar_str}]", True, bar_color
        )
        self.screen.blit(integrity_text, (10, 10))

        score_str = f"{self.score:08d} PTS"
        score_text = self.font_small.render(score_str, True, SCORE_YELLOW)
        score_rect = score_text.get_rect(centerx=WIDTH // 2, top=10)
        self.screen.blit(score_text, score_rect)

        mult_str = f"x{self.multiplier:.1f}"
        mult_scale = 1.0 + (self.multiplier - 1) * 0.05
        mult_color = (
            SCORE_YELLOW
            if self.multiplier < 4
            else ENEMY_RED
            if self.multiplier >= 8
            else PRISM_CYAN
        )
        mult_text = self.font_multiplier.render(mult_str, True, mult_color)

        if self.multiplier >= 8:
            offset = (random.uniform(-2, 2), random.uniform(-2, 2))
        else:
            offset = (0, 0)

        mult_rect = mult_text.get_rect(right=WIDTH - 10 + offset[0], top=10 + offset[1])
        self.screen.blit(mult_text, mult_rect)

        wave = WAVES[self.current_wave]
        wave_text = self.font_tiny.render(
            f"WAVE {self.current_wave + 1}: {wave.name}", True, INACTIVE_GREY
        )
        self.screen.blit(wave_text, (10, HEIGHT - 25))

        if self.time_dilation_timer > 0:
            dilation_text = self.font_small.render(
                f"TIME DILATION: {self.time_dilation_timer:.1f}s", True, PRISM_CYAN
            )
            dilation_rect = dilation_text.get_rect(
                centerx=WIDTH // 2, bottom=HEIGHT - 10
            )
            self.screen.blit(dilation_text, dilation_rect)

    def draw_game(self):
        offset = self.get_shake_offset()
        desat = self.get_desaturation()

        self.screen.fill(VOID_BLACK)
        self.draw_grid(self.screen, offset)

        score_text = self.font_score.render(str(self.score), True, (255, 255, 255))
        score_text.set_alpha(15)
        score_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(score_text, score_rect)

        for particle in self.particles:
            particle.draw(self.screen, offset)

        for spark in self.graze_sparks:
            spark.draw(self.screen, offset)

        for prism in self.prisms:
            prism.draw(self.screen, offset, desat)

        for powerup in self.powerups:
            powerup.draw(self.screen, offset, desat)

        for enemy in self.enemies:
            enemy.draw(self.screen, offset, desat)

        self.player.draw(self.screen, offset)

        self.draw_hud()

        if self.wave_transition:
            next_wave = (self.current_wave + 1) % len(WAVES)
            next_wave_name = WAVES[next_wave].name
            if self.current_wave + 1 >= len(WAVES):
                text = f"CYCLE {self.cycle + 1} INCOMING"
            else:
                text = f"NEXT: {next_wave_name}"
            wave_text = self.font_medium.render(text, True, PRISM_CYAN)
            wave_rect = wave_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
            self.screen.blit(wave_text, wave_rect)

        if self.invert_timer > 0:
            inv_surface = pygame.Surface((WIDTH, HEIGHT))
            inv_surface.fill((255, 255, 255))
            inv_surface.set_alpha(int(100 * (self.invert_timer / 0.5)))
            self.screen.blit(inv_surface, (0, 0), special_flags=pygame.BLEND_SUB)

    def draw_menu(self):
        self.screen.fill(VOID_BLACK)

        for i in range(10):
            x = 500 + random.uniform(-100, 100)
            y = 300 + random.uniform(-150, 150)
            for _ in range(5):
                jx = random.uniform(-8, 8)
                jy = random.uniform(-8, 8)
                pygame.draw.rect(
                    self.screen, ENEMY_RED, (int(x + jx), int(y + jy), 3, 3)
                )

        title1 = self.font_large.render("CHROMATIC", True, PLAYER_WHITE)
        title2 = self.font_large.render("DECAY", True, PLAYER_WHITE)
        title1_r = self.font_large.render("CHROMATIC", True, ENEMY_RED)
        title1_c = self.font_large.render("CHROMATIC", True, PRISM_CYAN)
        title2_r = self.font_large.render("DECAY", True, ENEMY_RED)
        title2_c = self.font_large.render("DECAY", True, PRISM_CYAN)

        self.screen.blit(title1_r, (48, 98))
        self.screen.blit(title1_c, (52, 102))
        self.screen.blit(title1, (50, 100))
        self.screen.blit(title2_r, (48, 168))
        self.screen.blit(title2_c, (52, 172))
        self.screen.blit(title2, (50, 170))

        version = self.font_tiny.render("v2.0", True, INACTIVE_GREY)
        self.screen.blit(version, (50, 250))

        options = ["[ START SEQUENCE ]", "[ TERMINATE ]"]
        for i, opt in enumerate(options):
            text = self.font_small.render(opt, True, TEXT_WHITE)
            self.screen.blit(text, (50, 400 + i * 40))

        controls = [
            "WASD/ARROWS: Move",
            "SPACE: Phase Dash",
            "Graze enemies for multiplier",
        ]
        for i, ctrl in enumerate(controls):
            text = self.font_tiny.render(ctrl, True, INACTIVE_GREY)
            self.screen.blit(text, (50, HEIGHT - 80 + i * 20))

        hint = self.font_small.render(
            "Press ENTER to start | ESC to quit", True, PRISM_CYAN
        )
        self.screen.blit(hint, (50, 500))

    def draw_pause(self):
        self.draw_game()
        self.draw_scanlines(self.screen)

        box_rect = pygame.Rect(200, 150, 400, 300)
        pygame.draw.rect(self.screen, VOID_BLACK, box_rect)
        pygame.draw.rect(self.screen, PLAYER_WHITE, box_rect, 2)

        if int(pygame.time.get_ticks() / 500) % 2 == 0:
            text = self.font_medium.render("SYSTEM HALTED", True, PLAYER_WHITE)
            text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30))
            self.screen.blit(text, text_rect)

        resume = self.font_small.render("Press ESC to resume", True, TEXT_WHITE)
        resume_rect = resume.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
        self.screen.blit(resume, resume_rect)

    def draw_gameover(self):
        self.screen.fill((20, 5, 5))

        for particle in self.death_particles:
            particle.update(1 / 60, 1.0)
            particle.vy += 100 * (1 / 60)
            particle.draw(self.screen, (0, 0))

        for _ in range(20):
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT)
            w = random.randint(10, 50)
            h = random.randint(10, 50)
            pygame.draw.rect(self.screen, ENEMY_RED, (x, y, w, h), 1)

        title = self.font_large.render("SIGNAL LOST", True, ENEMY_RED)
        title_rect = title.get_rect(center=(WIDTH // 2, 120))
        self.screen.blit(title, title_rect)

        stats = [
            f"SCORE: {self.score}",
            f"TIME SURVIVED: {int(self.time_survived)}s",
            f"WAVE REACHED: {self.current_wave + 1}",
            f"CYCLES: {self.cycle}",
            "",
            "[ R ] TO REBOOT",
            "[ ESC ] TO EXIT",
        ]
        for i, stat in enumerate(stats):
            color = TEXT_WHITE if i < 4 else PRISM_CYAN if "R" in stat else TEXT_WHITE
            text = self.font_small.render(stat, True, color)
            text_rect = text.get_rect(center=(WIDTH // 2, 220 + i * 35))
            self.screen.blit(text, text_rect)

    def handle_dash(self):
        if self.player.dash():
            self.spawn_particles(self.player.x, self.player.y, PRISM_CYAN, 10)

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
