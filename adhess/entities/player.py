from __future__ import annotations

import pygame

from adhess.animations import AnimationSet
from adhess.constants import (
    PLAYER_ATTACK_COOLDOWN,
    PLAYER_ATTACK_DAMAGE,
    PLAYER_ATTACK_DURATION,
    PLAYER_ATTACK_RADIUS,
    PLAYER_ATTACK_REACH,
    PLAYER_DAMAGE_FLASH_DURATION,
    PLAYER_DASH_COOLDOWN,
    PLAYER_DASH_DURATION,
    PLAYER_DASH_SPEED,
    PLAYER_MOVE_SPEED,
)
from adhess.utils import vector_to_direction_index


class Player:
    def __init__(self, position: tuple[float, float], animations: AnimationSet):
        self.position = pygame.Vector2(position)
        self.radius = 16
        self.speed = PLAYER_MOVE_SPEED
        self.direction = pygame.Vector2(0, 1)

        self.max_health = 100
        self.health = self.max_health
        self.damage_flash = 0.0

        self.attack_reach = PLAYER_ATTACK_REACH
        self.attack_radius = PLAYER_ATTACK_RADIUS
        self.attack_damage = PLAYER_ATTACK_DAMAGE
        self.attack_duration = PLAYER_ATTACK_DURATION
        self.attack_cooldown_time = PLAYER_ATTACK_COOLDOWN
        self.attack_timer = 0.0
        self.attack_cooldown = 0.0

        self.dash_speed = PLAYER_DASH_SPEED
        self.dash_duration = PLAYER_DASH_DURATION
        self.dash_cooldown_time = PLAYER_DASH_COOLDOWN
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0

        self.animations = animations

    def try_dash(self) -> bool:
        if self.dash_timer > 0 or self.dash_cooldown > 0:
            return False
        self.dash_timer = self.dash_duration
        self.dash_cooldown = self.dash_cooldown_time
        return True

    def start_attack(self) -> bool:
        if self.attack_timer > 0 or self.attack_cooldown > 0:
            return False
        self.attack_timer = self.attack_duration
        self.attack_cooldown = self.attack_cooldown_time
        self.animations.play("attack", restart=True)
        return True

    def take_damage(self, amount: float):
        self.health = max(0.0, self.health - amount)
        self.damage_flash = PLAYER_DAMAGE_FLASH_DURATION

    def heal(self, amount: float):
        self.health = min(self.max_health, self.health + amount)

    def update(self, dt: float, pressed):
        move = pygame.Vector2(0, 0)
        if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
            move.x -= 1
        if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
            move.x += 1
        if pressed[pygame.K_w] or pressed[pygame.K_UP]:
            move.y -= 1
        if pressed[pygame.K_s] or pressed[pygame.K_DOWN]:
            move.y += 1

        moving = move.length_squared() > 0
        if moving:
            move = move.normalize()
            self.direction = move
            self.position += move * self.speed * dt

        if self.dash_timer > 0:
            self.dash_timer = max(0.0, self.dash_timer - dt)
            self.position += self.direction * self.dash_speed * dt

        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)

        if self.attack_timer > 0:
            self.attack_timer = max(0.0, self.attack_timer - dt)

        if self.attack_timer > 0:
            desired_state = "attack"
        elif moving or self.dash_timer > 0:
            desired_state = "walk"
        else:
            desired_state = "idle"

        self.animations.play(desired_state)
        self.animations.update(dt)

        self.damage_flash = max(0.0, self.damage_flash - dt)

    @property
    def direction_index(self) -> int:
        return vector_to_direction_index(self.direction)

    @property
    def is_attacking(self) -> bool:
        return self.attack_timer > 0

    def current_frame(self):
        frame = self.animations.frame(self.direction_index)
        return frame if frame is not None else pygame.Surface((0, 0))
