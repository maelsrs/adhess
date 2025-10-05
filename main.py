import math
import random
import sys
from pathlib import Path
import pygame

SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
SCREEN_CENTER = pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
BACKGROUND_COLOR = (22, 22, 28)

def vector_to_direction_index(vector: pygame.Vector2) -> int:
    if vector.length_squared() == 0:
        return 0
    x, y = vector.x, vector.y
    if abs(x) > abs(y):
        return 2 if x > 0 else 1
    return 0 if y >= 0 else 3


def load_directional_frames(root: Path, prefix: str, scale: float = 1.0) -> list[list[pygame.Surface]]:
    frames = [
        pygame.image.load(str(root / f"{prefix}{index:03d}.png")).convert_alpha()
        for index in range(32)
    ]
    if scale != 1.0:
        frames = [pygame.transform.scale(frame, (int(frame.get_width() * scale), int(frame.get_height() * scale))) for frame in frames]
    return [frames[i * 8 : (i + 1) * 8] for i in range(4)]

class Player:
    def __init__(self, position: tuple[float, float], animations: dict[str, list[list[pygame.Surface]]]):
        self.position = pygame.Vector2(position)
        self.radius = 16
        self.speed = 220
        self.direction = pygame.Vector2(0, 1)

        self.max_health = 100
        self.health = self.max_health
        self.damage_flash_duration = 0.3
        self.damage_flash = 0.0

        self.animations = animations
        self.walk_fps = 10
        self.attack_fps = 20
        self.frame = 0.0
        self.state = "idle"

        self.attack_timer = 0.0
        self.attack_cooldown = 0.0
        self.attack_duration = 0.28
        self.attack_reach = 52
        self.attack_radius = 40
        self.attack_damage = 50

        self.dash_speed = 620
        self.dash_duration = 0.18
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0

    def try_dash(self) -> bool:
        if self.dash_timer > 0 or self.dash_cooldown > 0:
            return False
        self.dash_timer = self.dash_duration
        self.dash_cooldown = 0.55
        return True

    def start_attack(self) -> bool:
        if self.attack_timer > 0 or self.attack_cooldown > 0:
            return False
        self.attack_timer = self.attack_duration
        self.attack_cooldown = 0.22
        self.state = "attack"
        self.frame = 0.0
        return True

    def take_damage(self, amount: float):
        self.health = max(0.0, self.health - amount)
        self.damage_flash = self.damage_flash_duration

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
            self.frame += dt * self.attack_fps
            if self.attack_timer <= 0:
                self.state = "walk" if (moving or self.dash_timer > 0) else "idle"
                self.frame = 0.0
            return

        moving_now = moving or self.dash_timer > 0
        if moving_now:
            if self.state != "walk":
                self.frame = 0.0
            self.state = "walk"
            frames = self.animations["walk"][self.direction_index]
            self.frame = (self.frame + dt * self.walk_fps) % len(frames)
        else:
            self.state = "idle"
            self.frame = 0.0

        self.damage_flash = max(0.0, self.damage_flash - dt)

    @property
    def direction_index(self) -> int:
        return vector_to_direction_index(self.direction)

    @property
    def is_attacking(self) -> bool:
        return self.state == "attack" and self.attack_timer > 0

    def sprite(self) -> pygame.Surface:
        direction = self.direction_index
        if self.state == "attack":
            frames = self.animations["attack"][direction]
            index = min(len(frames) - 1, int(self.frame))
            return frames[index]
        frames = self.animations["walk"][direction]
        if self.state == "walk":
            index = int(self.frame) % len(frames)
            return frames[index]
        return frames[0]

class Enemy:
    def __init__(self, position: pygame.Vector2):
        self.position = pygame.Vector2(position)
        self.radius = 10
        self.speed = 110
        self.max_health = 60
        self.health = self.max_health
        self.attack_damage = 12
        self.attack_cooldown = 0.8
        self.attack_timer = 0.0

    def update(self, dt: float, target: pygame.Vector2):
        to_player = target - self.position
        if to_player.length_squared() > 0:
            direction = to_player.normalize()
            self.position += direction * self.speed * dt
        self.attack_timer = max(0.0, self.attack_timer - dt)

    def ready_to_attack(self, target_pos: pygame.Vector2, target_radius: float) -> bool:
        if self.attack_timer > 0:
            return False
        
        total_range = self.radius + target_radius + 3

        if (target_pos - self.position).length_squared() <= total_range * total_range:
            self.attack_timer = self.attack_cooldown
            return True
        return False

    def take_damage(self, amount: float):
        self.health -= amount

    @property
    def is_dead(self) -> bool:
        return self.health <= 0

    @property
    def health_ratio(self) -> float:
        return max(0.0, self.health / self.max_health)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("adhess")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        sprite_root = Path(__file__).resolve().parent / "assets" / "sprites" / "character" / "swordman"
        sprite_scale = 2
        animations = {
            "walk": load_directional_frames(sprite_root, "walk", sprite_scale),
            "attack": load_directional_frames(sprite_root, "attack", sprite_scale),
        }
        self.player = Player(SCREEN_CENTER, animations)
        self.player.radius = int(16 * sprite_scale)

        self.enemies: list[Enemy] = []
        self.wave = 0
        self.wave_active = False
        self.wave_delay = 1.0
        self.wave_timer = 0.0
        self.spawn_radius_min = 380
        self.spawn_radius_max = 520

        self.font = pygame.font.Font(None, 28)
        self.camera = pygame.Vector2()
        self.dash_effects = []
        self.dash_effect_timer = 0.0
        self.dash_effect_interval = 0.05
        self.dash_effect_lifetime = 0.22

        self.start_wave()

    def start_wave(self):
        self.wave += 1
        count = 3 + (self.wave - 1) * 2
        self.enemies = [self.create_enemy() for _ in range(count)]
        self.wave_active = True
        self.player.heal(self.player.max_health * 0.5)

    def create_enemy(self) -> Enemy:
        angle = random.uniform(0, math.tau)
        distance = random.uniform(self.spawn_radius_min, self.spawn_radius_max)
        offset = pygame.Vector2(math.cos(angle), math.sin(angle)) * distance
        return Enemy(self.player.position + offset)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                    self.running = False
                elif event.key in (pygame.K_SPACE, pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self.player.try_dash()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.player.start_attack():
                    self.apply_player_attack()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
               self.player.try_dash()

    def add_dash_effect(self):
        self.dash_effects.append({"pos": self.player.position.copy(), "life": self.dash_effect_lifetime})

    def apply_player_attack(self):
        center = self.player.position + self.player.direction * self.player.attack_reach
        reach = self.player.attack_radius
        for enemy in self.enemies:
            total_radius = reach + enemy.radius
            if (enemy.position - center).length_squared() <= total_radius * total_radius:
                enemy.take_damage(self.player.attack_damage)

    def update(self, dt: float):
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
        elif not self.wave_active:
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
        sprite = self.player.sprite()
        screen_position = self.player.position - self.camera
        rect = sprite.get_rect(center=(int(screen_position.x), int(screen_position.y)))
        self.screen.blit(sprite, rect)

        if self.player.damage_flash > 0:
            ratio = self.player.damage_flash / self.player.damage_flash_duration if self.player.damage_flash_duration else 0.0
            radius = int(self.player.radius * 0.8)
            size = radius * 2
            flash_surface = pygame.Surface((size, size), pygame.SRCALPHA)
            alpha = int(200 * ratio)
            pygame.draw.circle(flash_surface, (255, 80, 80, alpha), (radius, radius), radius)
            self.screen.blit(flash_surface, (screen_position.x - radius, screen_position.y - radius))

    def draw_enemies(self):
        for enemy in self.enemies:
            screen_pos = enemy.position - self.camera
            center = (int(screen_pos.x), int(screen_pos.y))
            pygame.draw.circle(self.screen, (200, 80, 80), center, enemy.radius)

            bar_width = enemy.radius * 2
            bar_height = 4
            bar_x = center[0] - bar_width // 2
            bar_y = center[1] + enemy.radius + 4
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

if __name__ == "__main__":
    main()






