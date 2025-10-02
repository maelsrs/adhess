import random
import sys
import pygame

SCREEN_WIDTH, SCREEN_HEIGHT = 960, 540
BACKGROUND_COLOR = (18, 18, 24)
GRID_COLOR = (32, 32, 42)


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

    def draw(self):
        self.screen.fill(BACKGROUND_COLOR)

        # draw player
        pygame.draw.circle(self.screen, (200, 200, 200), self.player.position, 10)

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
