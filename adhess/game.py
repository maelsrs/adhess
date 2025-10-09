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

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("adhess")
        self.screen = pygame.display.set_mode(SCREEN_SIZE)
        self.clock = pygame.time.Clock()
        self.running = True

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
        self.player = Player(SCREEN_CENTER, AnimationSet(player_anim_data))
        self.player.radius = int(16 * swordman_scale)

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
        self.wave_delay = 1.0
        self.wave_timer = 0.0
        self.spawn_radius_min = 380
        self.spawn_radius_max = 520

        self.font = pygame.font.Font(None, 28)
        self.upgrade_title_font = pygame.font.Font(None, 48)
        self.upgrade_option_font = pygame.font.Font(None, 32)
        self.upgrade_description_font = pygame.font.Font(None, 24)
        self.camera = pygame.Vector2()
        self.dash_effects = []
        self.dash_effect_timer = 0.0
        self.dash_effect_interval = 0.05
        self.dash_effect_lifetime = 0.22

        self.upgrade_popup_active = False
        self.upgrade_selected_index = 0
        self.upgrade_option_rects = []
        self.all_upgrades = self.build_upgrade_choices()
        self.upgrade_choices = []

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
        return Enemy(self.player.position + offset, self.clone_enemy_animation(), self.enemy_radius)

    def build_upgrade_choices(self):
        return [
            {
                "key": "max_health",
                "label": "Vie max +20%",
                "description": "Augmente la vie maximale et soigne du bonus.",
                "apply": self._upgrade_max_health,
            },
            {
                "key": "attack_damage",
                "label": "Dégâts +10",
                "description": "Renforce les attaques de mêlée.",
                "apply": self._upgrade_attack_damage,
            },
            {
                "key": "move_speed",
                "label": "Vitesse +12%",
                "description": "Accélère les déplacements.",
                "apply": self._upgrade_move_speed,
            },
            {
                "key": "attack_range",
                "label": "Portée attaque +10%",
                "description": "Allonge la portée et la largeur de l'attaque.",
                "apply": self._upgrade_attack_range,
            },
            {
                "key": "dash_speed",
                "label": "Dash vitesse +15%",
                "description": "Rend les dashs plus explosifs.",
                "apply": self._upgrade_dash_speed,
            },
            {
                "key": "attack_cooldown",
                "label": "Cooldown attaque -10%",
                "description": "Permet d'enchaîner les coups plus vite.",
                "apply": self._upgrade_attack_cooldown,
            },
            {
                "key": "dash_cooldown",
                "label": "Cooldown dash -15%",
                "description": "Réduit l'attente entre deux dashs.",
                "apply": self._upgrade_dash_cooldown,
            },
        ]

    def _upgrade_max_health(self):
        bonus = max(10, int(self.player.max_health * 0.2))
        self.player.max_health += bonus
        self.player.health = min(self.player.max_health, self.player.health + bonus)

    def _upgrade_attack_damage(self):
        self.player.attack_damage += 10

    def _upgrade_move_speed(self):
        self.player.speed *= 1.12

    def _upgrade_attack_range(self):
        self.player.attack_reach *= 1.1
        self.player.attack_radius *= 1.1

    def _upgrade_dash_speed(self):
        self.player.dash_speed *= 1.15

    def _upgrade_attack_cooldown(self):
        self.player.attack_cooldown_time = max(0.05, self.player.attack_cooldown_time * 0.9)
        self.player.attack_cooldown = min(self.player.attack_cooldown, self.player.attack_cooldown_time)

    def _upgrade_dash_cooldown(self):
        self.player.dash_cooldown_time = max(0.1, self.player.dash_cooldown_time * 0.85)
        self.player.dash_cooldown = min(self.player.dash_cooldown, self.player.dash_cooldown_time)

    def trigger_upgrade_selection(self):
        if self.upgrade_popup_active or not self.all_upgrades:
            return
        sample_size = min(3, len(self.all_upgrades))
        self.upgrade_choices = random.sample(self.all_upgrades, k=sample_size)
        self.upgrade_popup_active = True
        self.upgrade_selected_index = 0
        self.upgrade_option_rects = []
        self.player.animations.play("idle", restart=True)
        self.player.attack_timer = 0.0
        self.player.dash_timer = 0.0

    def handle_upgrade_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.key in (pygame.K_UP, pygame.K_w):
                self.upgrade_selected_index = (self.upgrade_selected_index - 1) % len(self.upgrade_choices)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.upgrade_selected_index = (self.upgrade_selected_index + 1) % len(self.upgrade_choices)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.apply_selected_upgrade()
        elif event.type == pygame.MOUSEMOTION:
            for index, rect in enumerate(self.upgrade_option_rects):
                if rect.collidepoint(event.pos):
                    self.upgrade_selected_index = index
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for index, rect in enumerate(self.upgrade_option_rects):
                if rect.collidepoint(event.pos):
                    self.upgrade_selected_index = index
                    self.apply_selected_upgrade()
                    break

    def apply_selected_upgrade(self):
        if not self.upgrade_choices:
            self.upgrade_popup_active = False
            return
        choice = self.upgrade_choices[self.upgrade_selected_index]
        choice["apply"]()
        self.upgrade_popup_active = False
        self.upgrade_option_rects = []
        self.wave_timer = max(self.wave_timer, self.wave_delay)

    def draw_upgrade_overlay(self):
        overlay = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        overlay.fill((12, 12, 18, 210))
        self.screen.blit(overlay, (0, 0))

        center_x = SCREEN_SIZE[0] // 2
        center_y = SCREEN_SIZE[1] // 2

        box_width = 520
        box_height = 62
        spacing = 12
        total_height = len(self.upgrade_choices) * box_height + (len(self.upgrade_choices) - 1) * spacing
        start_y = center_y - total_height // 2

        title_surface = self.upgrade_title_font.render("Amélioration disponible", True, (240, 240, 240))
        title_rect = title_surface.get_rect(center=(center_x, start_y - 60))
        self.screen.blit(title_surface, title_rect)

        instruction_surface = self.upgrade_description_font.render("Entrée pour valider · Échap pour quitter", True, (200, 200, 200))
        instruction_rect = instruction_surface.get_rect(center=(center_x, start_y + total_height + 40))
        self.screen.blit(instruction_surface, instruction_rect)

        option_rects = []
        for index, choice in enumerate(self.upgrade_choices):
            rect = pygame.Rect(0, 0, box_width, box_height)
            rect.centerx = center_x
            rect.y = start_y + index * (box_height + spacing)

            is_selected = index == self.upgrade_selected_index
            base_color = (54, 58, 84) if is_selected else (36, 38, 56)
            border_color = (120, 140, 220) if is_selected else (80, 86, 120)

            pygame.draw.rect(self.screen, base_color, rect, border_radius=10)
            pygame.draw.rect(self.screen, border_color, rect, width=2, border_radius=10)

            label_surface = self.upgrade_option_font.render(choice["label"], True, (240, 240, 240))
            label_rect = label_surface.get_rect()
            label_rect.topleft = (rect.x + 20, rect.y + 8)
            self.screen.blit(label_surface, label_rect)

            description_surface = self.upgrade_description_font.render(choice["description"], True, (200, 200, 200))
            description_rect = description_surface.get_rect()
            description_rect.topleft = (rect.x + 20, rect.y + 36)
            self.screen.blit(description_surface, description_rect)

            option_rects.append(rect)

        self.upgrade_option_rects = option_rects

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if self.upgrade_popup_active:
                self.handle_upgrade_event(event)
                continue
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT):
                    if self.player.try_dash():
                        self.add_dash_effect()
                        self.dash_effect_timer = self.dash_effect_interval
            elif event.type == pygame.MOUSEBUTTONDOWN:
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
        if self.upgrade_popup_active:
            self.player.animations.play("idle")
            self.player.animations.update(dt)
            self.player.damage_flash = max(0.0, self.player.damage_flash - dt)
            self.dash_effect_timer = 0.0
            for effect in self.dash_effects:
                effect["life"] = max(0.0, effect["life"] - dt)
            self.dash_effects = [effect for effect in self.dash_effects if effect["life"] > 0]
            self.camera = self.player.position - SCREEN_CENTER
            return

        pressed = pygame.key.get_pressed()
        self.player.update(dt, pressed)

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
            if enemy.ready_to_attack(self.player.position, self.player.radius):
                self.player.take_damage(enemy.attack_damage)
        self.enemies = [enemy for enemy in self.enemies if not enemy.is_dead]

        if self.wave_active and not self.enemies:
            self.wave_active = False
            self.wave_timer = self.wave_delay
            if self.wave % 5 == 0:
                self.trigger_upgrade_selection()
        elif not self.wave_active and not self.upgrade_popup_active:
            self.wave_timer = max(0.0, self.wave_timer - dt)
            if self.wave_timer <= 0.0:
                self.start_wave()

        if self.player.health <= 0:
            self.running = False

        self.camera = self.player.position - SCREEN_CENTER

    def draw_dash_effects(self):
        for effect in self.dash_effects:
            ratio = effect["life"] / self.dash_effect_lifetime if self.dash_effect_lifetime else 0.0
            size = max(3, int(18 * ratio))
            alpha = max(30, int(200 * ratio))
            surface = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surface, (255, 255, 255, alpha), (size, size), size)
            pos = effect["pos"] - self.camera
            self.screen.blit(surface, (pos.x - size, pos.y - size))

    def draw_player(self):
        sprite = self.player.current_frame()
        screen_position = self.player.position - self.camera
        rect = sprite.get_rect(center=(int(screen_position.x), int(screen_position.y)))
        self.screen.blit(sprite, rect)

        if self.player.damage_flash > 0:
            ratio = self.player.damage_flash / PLAYER_DAMAGE_FLASH_DURATION if PLAYER_DAMAGE_FLASH_DURATION else 0.0
            radius = max(12, int(self.player.radius * 1.6))
            size = radius * 2
            flash_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            alpha = int(200 * ratio)
            pygame.draw.circle(flash_surface, (255, 80, 80, alpha), (radius, radius), radius)
            self.screen.blit(flash_surface, (screen_position.x - radius, screen_position.y - radius))

    def draw_enemies(self):
        for enemy in self.enemies:
            screen_pos = enemy.position - self.camera
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

    def draw_ui(self):
        lines = [
            f"HP: {int(self.player.health)}/{self.player.max_health}",
            f"Vague {self.wave}",
            f"Ennemis: {len(self.enemies)}",
        ]
        if not self.wave_active:
            if self.upgrade_popup_active:
                lines.append("Amélioration disponible !")
            else:
                lines.append(f"Prochaine vague dans {self.wave_timer:.1f}s")
        for index, text in enumerate(lines):
            surface = self.font.render(text, True, (230, 230, 230))
            self.screen.blit(surface, (20, 20 + index * 22))

    def draw(self):
        self.screen.fill(BACKGROUND_COLOR)
        self.draw_enemies()
        self.draw_dash_effects()
        self.draw_player()
        self.draw_ui()
        if self.upgrade_popup_active:
            self.draw_upgrade_overlay()
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
