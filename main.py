import random
import sys
import pygame

SCREEN_WIDTH, SCREEN_HEIGHT = 960, 540
SCREEN_CENTER = pygame.Vector2(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
BACKGROUND_COLOR = (18, 18, 24)
GRID_COLOR = (32, 32, 42)
GRID_SPACING = 64


class Character:
    def __init__(self, name):
        self.name = name
        self.health = 100
        self.max_health = 100
        self.speed = 1


class Player(Character):
    def __init__(self, position):
        super().__init__("")
        self.position = pygame.Vector2(position)
        self.dash_timer = 0
        self.dash_cooldown = 0

    def update(self, dt, pressed):
        direction = pygame.Vector2(0, 0)
        if pressed[pygame.K_w] or pressed[pygame.K_UP]:
            direction.y -= 1
        if pressed[pygame.K_s] or pressed[pygame.K_DOWN]:
            direction.y += 1
        if pressed[pygame.K_a] or pressed[pygame.K_LEFT]:
            direction.x -= 1
        if pressed[pygame.K_d] or pressed[pygame.K_RIGHT]:
            direction.x += 1

        speed = self.speed
        if direction.length_squared() > 0:
            direction = direction.normalize()
            self.position += direction * speed * dt * 200


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("adhess")

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        self.player = Player((SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
        self.camera_offset = pygame.Vector2()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self, dt):
        pressed = pygame.key.get_pressed()
        self.player.update(dt, pressed)
        self.camera_offset = self.player.position - SCREEN_CENTER

    def draw_grid(self):
        start_x = int(-self.camera_offset.x % GRID_SPACING)
        start_y = int(-self.camera_offset.y % GRID_SPACING)
        width, height = self.screen.get_size()

        for x in range(start_x, width, GRID_SPACING):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, height))

        for y in range(start_y, height, GRID_SPACING):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (width, y))

    def draw(self):
        self.screen.fill(BACKGROUND_COLOR)
        self.draw_grid()

        player_screen_pos = self.player.position - self.camera_offset
        pygame.draw.circle(self.screen, (200, 200, 200), player_screen_pos, 10)

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
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
