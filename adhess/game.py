import math
import random
import sys
from pathlib import Path

import pygame

from adhess.animations import AnimationSet, build_idle_frames, load_directional_frames
from adhess.constants import (
    BACKGROUND_COLOR,
    ENEMY_ATTACK_DURATION,
    ENEMY_HURT_DURATION,
    ENEMY_WALK_FPS,
    PLAYER_ATTACK_DURATION,
    PLAYER_DAMAGE_FLASH_DURATION,
    PLAYER_WALK_FPS,
    SCREEN_CENTER,
    SCREEN_SIZE,
)
from adhess.entities.enemy import Enemy
from adhess.entities.player import Player
from adhess.map import GameMap

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"

PLAYER_COLLISION_TYPES = ("interior", "exterior")
ENEMY_COLLISION_TYPES = ("interior",)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("adhess")
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.clock = pygame.time.Clock()
        self.running = True

        self.map = GameMap(ASSETS_DIR / "maps" / "2.png", ASSETS_DIR / "maps" / "2_collisions.json")
        screen_w, screen_h = SCREEN_SIZE
        self.map_offset = pygame.Vector2(
            max(0, (screen_w - self.map.rect.width) / 2),
            max(0, (screen_h - self.map.rect.height) / 2),
        )

        swordman_root = ASSETS_DIR / "sprites" / "character" / "swordman"
        swordman_scale = 1.8
        swordman_walk_frames = load_directional_frames(swordman_root, "walk", 32, 8, swordman_scale)
        swordman_attack_frames = load_directional_frames(swordman_root, "attack", 32, 8, swordman_scale)
        swordman_idle_frames = build_idle_frames(swordman_walk_frames)
        player_anim_data = {
            "idle": {"frames": swordman_idle_frames, "fps": 0, "loop": False},
            "walk": {"frames": swordman_walk_frames, "fps": PLAYER_WALK_FPS, "loop": True},
        }
        attack_fps = len(swordman_attack_frames[0]) / PLAYER_ATTACK_DURATION if PLAYER_ATTACK_DURATION > 0 else PLAYER_WALK_FPS
        player_anim_data["attack"] = {
            "frames": swordman_attack_frames,
            "fps": attack_fps,
            "loop": False,
            "duration": PLAYER_ATTACK_DURATION,
        }
        self.player = Player(self.map.rect.center, AnimationSet(player_anim_data))
        self.player.radius = int(16 * swordman_scale)
        self.player.position = pygame.Vector2(self.map.rect.center)
        self.map.resolve_collisions(self.player.position, self.player.radius, PLAYER_COLLISION_TYPES)

        goblin_root = ASSETS_DIR / "sprites" / "mobs" / "goblin"
        goblin_scale = 1.35
        goblin_order = [0, 2, 3, 1]
        goblin_walk_frames = load_directional_frames(goblin_root, "walk", 24, 6, goblin_scale, goblin_order)
        goblin_attack_frames = load_directional_frames(goblin_root, "attack", 24, 6, goblin_scale, goblin_order)
        goblin_hurt_frames = load_directional_frames(goblin_root, "hurt", 24, 6, goblin_scale, goblin_order)
        goblin_anim_data = {
            "walk": {"frames": goblin_walk_frames, "fps": ENEMY_WALK_FPS, "loop": True},
            "attack": {
                "frames": goblin_attack_frames,
                "fps": len(goblin_attack_frames[0]) / ENEMY_ATTACK_DURATION if ENEMY_ATTACK_DURATION > 0 else ENEMY_WALK_FPS,
                "loop": False,
                "duration": ENEMY_ATTACK_DURATION,
            },
            "hurt": {
                "frames": goblin_hurt_frames,
                "fps": len(goblin_hurt_frames[0]) / ENEMY_HURT_DURATION if ENEMY_HURT_DURATION > 0 else ENEMY_WALK_FPS,
                "loop": False,
                "duration": ENEMY_HURT_DURATION,
            },
        }
        walk_frames_sample = goblin_walk_frames[0]
        if walk_frames_sample:
            self.enemy_radius = max(8, walk_frames_sample[0].get_width() // 3)
        else:
            self.enemy_radius = 10

        self.enemy_anim_template = AnimationSet(goblin_anim_data)

        self.enemies = []
        self.wave = 0
        self.wave_active = False
        self.wave_delay = 4.0
        self.wave_timer = 0.0
        self.spawn_radius_min = 380
        self.spawn_radius_max = 520

        self.font = pygame.font.Font(None, 28)
        self.debug_font = pygame.font.Font(None, 20)
        self.debug_show_collisions = False
        self.camera = pygame.Vector2()
        self.dash_effects = []
        self.dash_effect_timer = 0.0
        self.dash_effect_interval = 0.05
        self.dash_effect_lifetime = 0.22

        self.start_wave()

    def clone_enemy_animation(self):
        data_copy = {}
        for state, info in self.enemy_anim_template.data.items():
            data_copy[state] = {
                "frames": info["frames"],
                "fps": info.get("fps", 0),
                "loop": info.get("loop", True),
                "duration": info.get("duration"),
            }
        return AnimationSet(data_copy)

    def start_wave(self):
        self.wave += 1
        count = 3 + (self.wave - 1) * 2
        self.enemies = [self.create_enemy() for _ in range(count)]
        self.wave_active = True
        self.player.heal(self.player.max_health * 0.5)

    def create_enemy(self):
        angle = random.uniform(0, math.tau)
        distance = random.uniform(self.spawn_radius_min, self.spawn_radius_max)
        offset = pygame.Vector2(math.cos(angle), math.sin(angle)) * distance
        spawn_position = self.player.position + offset
        enemy = Enemy(spawn_position, self.clone_enemy_animation(), self.enemy_radius)
        self.map.resolve_collisions(enemy.position, enemy.radius, ENEMY_COLLISION_TYPES)
        return enemy

    def world_to_screen(self, position):
        return position - self.camera + self.map_offset

    def screen_to_world(self, position):
        screen_pos = pygame.Vector2(position)
        return screen_pos + self.camera - self.map_offset

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_F1:
                    self.debug_show_collisions = not self.debug_show_collisions
                elif event.key in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT):
                    if self.player.try_dash():
                        self.add_dash_effect()
                        self.dash_effect_timer = self.dash_effect_interval
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.debug_show_collisions:
                    world_pos = self.screen_to_world(event.pos)
                    print(f"cos : {int(world_pos.x)}, {int(world_pos.y)}")
                if event.button == 1:
                    if self.player.start_attack():
                        self.apply_player_attack()
                elif event.button == 3:
                    if self.player.try_dash():
                        self.add_dash_effect()
                        self.dash_effect_timer = self.dash_effect_interval

    def add_dash_effect(self):
        self.dash_effects.append({"pos": self.player.position.copy(), "life": self.dash_effect_lifetime})

    def apply_player_attack(self):
        center = self.player.position + self.player.direction * self.player.attack_reach
        reach = self.player.attack_radius
        for enemy in self.enemies:
            total_radius = reach + enemy.radius
            if (enemy.position - center).length_squared() <= total_radius * total_radius:
                enemy.take_damage(self.player.attack_damage)

    def update(self, dt):
        pressed = pygame.key.get_pressed()
        self.player.update(dt, pressed)
        self.map.resolve_collisions(self.player.position, self.player.radius, PLAYER_COLLISION_TYPES)

        if self.player.dash_timer > 0:
            self.dash_effect_timer -= dt
            if self.dash_effect_timer <= 0.0:
                self.add_dash_effect()
                self.dash_effect_timer = self.dash_effect_interval
        else:
            self.dash_effect_timer = 0.0

        for effect in self.dash_effects:
            effect["life"] -= dt
        self.dash_effects = [effect for effect in self.dash_effects if effect["life"] > 0]

        for enemy in self.enemies:
            enemy.update(dt, self.player.position)
            self.map.resolve_collisions(enemy.position, enemy.radius, ENEMY_COLLISION_TYPES)
            if enemy.ready_to_attack(self.player.position, self.player.radius):
                self.player.take_damage(enemy.attack_damage)
                break
        self.enemies = [enemy for enemy in self.enemies if not enemy.is_dead]

        if self.wave_active and not self.enemies:
            self.wave_active = False
            self.wave_timer = self.wave_delay
        elif not self.wave_active:
            self.wave_timer = max(0.0, self.wave_timer - dt)
            if self.wave_timer <= 0.0:
                self.start_wave()

        if self.player.health <= 0:
            self.running = False

        desired_camera = self.player.position - SCREEN_CENTER
        map_w, map_h = self.map.rect.size
        screen_w, screen_h = SCREEN_SIZE
        max_x = max(0, map_w - screen_w)
        max_y = max(0, map_h - screen_h)
        self.camera.x = max(0, min(desired_camera.x, max_x))
        self.camera.y = max(0, min(desired_camera.y, max_y))

    def draw_dash_effects(self):
        for effect in self.dash_effects:
            ratio = effect["life"] / self.dash_effect_lifetime if self.dash_effect_lifetime else 0.0
            size = max(3, int(18 * ratio))
            alpha = max(30, int(200 * ratio))
            surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surface, (255, 255, 255, alpha), (size, size), size)
            pos = self.world_to_screen(effect["pos"])
            self.screen.blit(surface, (int(pos.x - size), int(pos.y - size)))

    def draw_player(self):
        sprite = self.player.current_frame()
        screen_position = self.world_to_screen(self.player.position)
        rect = sprite.get_rect(center=(int(screen_position.x), int(screen_position.y)))
        self.screen.blit(sprite, rect)

        if self.player.damage_flash > 0:
            ratio = self.player.damage_flash / PLAYER_DAMAGE_FLASH_DURATION if PLAYER_DAMAGE_FLASH_DURATION else 0.0
            radius = max(12, int(self.player.radius * 1.6))
            size = radius * 2
            flash_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            alpha = int(200 * ratio)
            pygame.draw.circle(flash_surface, (255, 80, 80, alpha), (radius, radius), radius)
            self.screen.blit(flash_surface, (int(screen_position.x - radius), int(screen_position.y - radius)))

    def draw_enemies(self):
        for enemy in self.enemies:
            screen_pos = self.world_to_screen(enemy.position)
            sprite = enemy.current_frame()
            if sprite is not None:
                rect = sprite.get_rect(center=(int(screen_pos.x), int(screen_pos.y)))
                self.screen.blit(sprite, rect)

            bar_width = max(20, enemy.radius * 2)
            bar_height = 4
            bar_x = int(screen_pos.x - bar_width / 2)
            bar_y = int(screen_pos.y + enemy.radius + 4)
            pygame.draw.rect(self.screen, (60, 30, 30), (bar_x, bar_y, bar_width, bar_height))
            pygame.draw.rect(
                self.screen,
                (200, 80, 80),
                (bar_x, bar_y, int(bar_width * enemy.health_ratio), bar_height),
            )

    def draw_debug_overlay(self):
        if not self.debug_show_collisions:
            return

        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        offset_x = -self.camera.x + self.map_offset.x
        offset_y = -self.camera.y + self.map_offset.y

        type_styles = {
            "interior": ((255, 60, 60, 60), (255, 80, 80, 180)),
            "exterior": ((60, 120, 255, 60), (80, 160, 255, 180)),
        }
        default_style = ((255, 60, 60, 60), (255, 80, 80, 180))

        for rect, rect_type in self.map.iter_collision_entries():
            debug_rect = pygame.Rect(rect)
            debug_rect.x = int(debug_rect.x + offset_x)
            debug_rect.y = int(debug_rect.y + offset_y)
            fill_color, outline_color = type_styles.get(rect_type, default_style)
            pygame.draw.rect(overlay, fill_color, debug_rect)
            pygame.draw.rect(overlay, outline_color, debug_rect, 2)

        info_lines = [
            "[F1] collisions",
            "Click to get collisinos",
        ]

        max_width = max(self.debug_font.size(line)[0] for line in info_lines)
        line_height = self.debug_font.get_linesize()
        padding = 8
        info_height = line_height * len(info_lines)
        info_surface = pygame.Surface((max_width + padding * 2, info_height + padding * 2), pygame.SRCALPHA)
        info_surface.fill((20, 20, 20, 190))

        for index, line in enumerate(info_lines):
            line_surface = self.debug_font.render(line, True, (240, 240, 240))
            info_surface.blit(line_surface, (padding, padding + index * line_height))

        overlay.blit(info_surface, (self.screen.get_width() - info_surface.get_width() - 20, 20))
        self.screen.blit(overlay, (0, 0))

    def draw_ui(self):
        lines = [
            f"HP: {int(self.player.health)}/{self.player.max_health}",
            f"Vague {self.wave}",
            f"Ennemis: {len(self.enemies)}",
        ]
        if not self.wave_active:
            lines.append(f"Prochaine vague dans {self.wave_timer:.1f}s")
        for index, text in enumerate(lines):
            surface = self.font.render(text, True, (230, 230, 230))
            self.screen.blit(surface, (20, 20 + index * 22))

    def draw(self):
        self.screen.fill(BACKGROUND_COLOR)
        self.map.draw(self.screen, self.camera, self.map_offset)
        self.draw_enemies()
        self.draw_dash_effects()
        self.draw_player()
        self.draw_debug_overlay()
        self.draw_ui()
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()


def main():
    Game().run()
