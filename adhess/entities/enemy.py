import pygame

from adhess.constants import (
    ENEMY_ATTACK_COOLDOWN,
    ENEMY_ATTACK_DAMAGE,
    ENEMY_ATTACK_DURATION,
    ENEMY_HURT_DURATION,
    ENEMY_MOVE_SPEED,
)
from adhess.utils import vector_to_direction_index


class Enemy:
    def __init__(self, position, animations, radius):
        self.position = pygame.Vector2(position)
        self.radius = radius
        self.speed = ENEMY_MOVE_SPEED
        self.max_health = 60
        self.health = self.max_health

        self.attack_damage = ENEMY_ATTACK_DAMAGE
        self.attack_cooldown_time = ENEMY_ATTACK_COOLDOWN
        self.attack_timer = 0.0

        self.attack_duration = ENEMY_ATTACK_DURATION
        self.attack_anim_timer = 0.0
        self.hurt_duration = ENEMY_HURT_DURATION
        self.hurt_timer = 0.0

        self.direction = pygame.Vector2(0, 1)
        self.animations = animations

    def update(self, dt, target):
        to_player = target - self.position
        if to_player.length_squared() > 0:
            self.direction = to_player.normalize()

        can_move = self.hurt_timer <= 0 and self.attack_anim_timer <= 0
        if can_move and to_player.length_squared() > 0:
            self.position += self.direction * self.speed * dt

        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.hurt_timer = max(0.0, self.hurt_timer - dt)
        self.attack_anim_timer = max(0.0, self.attack_anim_timer - dt)

        if self.animations.state == "hurt" and self.hurt_timer <= 0:
            self.animations.play("walk", restart=True)
        if self.animations.state == "attack" and self.attack_anim_timer <= 0:
            self.animations.play("walk", restart=True)

        if self.animations.state not in {"attack", "hurt"}:
            self.animations.play("walk")

        self.animations.update(dt)

    def ready_to_attack(self, target_pos, target_radius):
        if self.attack_timer > 0:
            return False
        total_range = self.radius + target_radius + 6
        if (target_pos - self.position).length_squared() <= total_range * total_range:
            self.attack_timer = self.attack_cooldown_time
            self.attack_anim_timer = self.attack_duration
            self.animations.play("attack", restart=True)
            return True
        return False

    def take_damage(self, amount):
        self.health -= amount
        if self.health > 0:
            self.hurt_timer = self.hurt_duration
            self.animations.play("hurt", restart=True)

    @property
    def is_dead(self):
        return self.health <= 0

    @property
    def health_ratio(self):
        return max(0.0, self.health / self.max_health)

    @property
    def direction_index(self):
        return vector_to_direction_index(self.direction)

    def current_frame(self):
        return self.animations.frame(self.direction_index)
