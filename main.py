import math
import random
import sys
from pathlib import Path
import pygame

SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
SCREEN_CENTER = pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
BACKGROUND_COLOR = (22, 22, 28)

PLAYER_ATTACK_DURATION = 0.28
PLAYER_ATTACK_COOLDOWN = 0.22
PLAYER_DASH_DURATION = 0.18
PLAYER_DASH_COOLDOWN = 0.55
PLAYER_WALK_FPS = 10
PLAYER_ATTACK_DAMAGE = 50
PLAYER_ATTACK_REACH = 52
PLAYER_ATTACK_RADIUS = 40
PLAYER_MOVE_SPEED = 220
PLAYER_DASH_SPEED = 620
PLAYER_DAMAGE_FLASH_DURATION = 0.3

ENEMY_WALK_FPS = 8
ENEMY_ATTACK_DURATION = 0.35
ENEMY_HURT_DURATION = 0.25
ENEMY_ATTACK_COOLDOWN = 0.8
ENEMY_ATTACK_DAMAGE = 12
ENEMY_MOVE_SPEED = 90


def vector_to_direction_index(vector: pygame.Vector2) -> int:
    if vector.length_squared() == 0:
        return 0
    x, y = vector.x, vector.y
    if abs(x) > abs(y):
        return 2 if x > 0 else 1
    return 0 if y >= 0 else 3

def load_directional_frames(
    root: Path,
    prefix: str,
    frame_count: int,
    frames_per_direction: int,
    scale: float = 1.0,
    direction_order: list[int] | None = None,
) -> list[list[pygame.Surface]]:
    frames: list[pygame.Surface] = []
    for index in range(frame_count):
        image_path = root / f"{prefix}{index:03d}.png"
        surface = pygame.image.load(str(image_path)).convert_alpha()
        if scale != 1.0:
            width = max(1, int(surface.get_width() * scale))
            height = max(1, int(surface.get_height() * scale))
            surface = pygame.transform.smoothscale(surface, (width, height))
        frames.append(surface)

    directions = [frames[i * frames_per_direction : (i + 1) * frames_per_direction] for i in range(4)]
    if direction_order is not None:
        directions = [directions[i] for i in direction_order]
    return directions


def build_idle_frames(walk_frames: list[list[pygame.Surface]]) -> list[list[pygame.Surface]]:
    idle = []
    for direction_frames in walk_frames:
        idle.append([direction_frames[0]] if direction_frames else [])
    return idle

class AnimationSet:
    def __init__(self, data: dict[str, dict]):
        self.data = data
        self.state = next(iter(data))
        self.time = 0.0

    def play(self, state: str, restart: bool = False):
        if state not in self.data:
            return
        if state != self.state or restart:
            self.state = state
            self.time = 0.0

    def update(self, dt: float):
        self.time += dt

    def frame(self, direction: int) -> pygame.Surface | None:
        info = self.data[self.state]
        frames = info["frames"][direction]
        if not frames:
            return None

        duration = info.get("duration")
        fps = info.get("fps", 0)
        loop = info.get("loop", True)

        if duration:
            progress = min(1.0, self.time / duration)
            index = min(len(frames) - 1, int(progress * len(frames)))
            return frames[index]

        if fps <= 0:
            return frames[0]

        index = int(self.time * fps)
        if loop:
            index %= len(frames)
        else:
            index = min(len(frames) - 1, index)
        return frames[index]


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


class Enemy:
    def __init__(self, position, animations: AnimationSet, radius: int):
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

    def update(self, dt: float, target):
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

    def ready_to_attack(self, target_pos, target_radius: float) -> bool:
        if self.attack_timer > 0:
            return False
        total_range = self.radius + target_radius + 6
        if (target_pos - self.position).length_squared() <= total_range * total_range:
            self.attack_timer = self.attack_cooldown_time
            self.attack_anim_timer = self.attack_duration
            self.animations.play("attack", restart=True)
            return True
        return False

    def take_damage(self, amount: float):
        self.health -= amount
        if self.health > 0:
            self.hurt_timer = self.hurt_duration
            self.animations.play("hurt", restart=True)

    @property
    def is_dead(self) -> bool:
        return self.health <= 0

    @property
    def health_ratio(self) -> float:
        return max(0.0, self.health / self.max_health)

    @property
    def direction_index(self) -> int:
        return vector_to_direction_index(self.direction)

    def current_frame(self):
        return self.animations.frame(self.direction_index)

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("adhess")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        swordman_root = Path(__file__).resolve().parent / "assets" / "sprites" / "character" / "swordman"
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

        goblin_root = Path(__file__).resolve().parent / "assets" / "sprites"  / "mobs" / "goblin"
        goblin_scale = 1.35
        goblin_order = [0, 2, 3, 1]  # bas, gauche, droite, haut
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

        self.enemies: list[Enemy] = []
        self.wave = 0
        self.wave_active = False
        self.wave_delay = 1.0
        self.wave_timer = 0.0
        self.spawn_radius_min = 380
        self.spawn_radius_max = 520

        self.font = pygame.font.Font(None, 28)
        self.camera = pygame.Vector2()
        self.dash_effects: list[dict[str, float | pygame.Vector2]] = []
        self.dash_effect_timer = 0.0
        self.dash_effect_interval = 0.05
        self.dash_effect_lifetime = 0.22

        self.start_wave()

    def clone_enemy_animation(self) -> AnimationSet:
        data_copy: dict[str, dict] = {}
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

    def create_enemy(self) -> Enemy:
        angle = random.uniform(0, math.tau)
        distance = random.uniform(self.spawn_radius_min, self.spawn_radius_max)
        offset = pygame.Vector2(math.cos(angle), math.sin(angle)) * distance
        return Enemy(self.player.position + offset, self.clone_enemy_animation(), self.enemy_radius)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
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
