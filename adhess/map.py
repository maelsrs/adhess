import json
import os

import pygame


def _clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


class GameMap:
    def __init__(self, image_path, collision_path=None):
        self.image_path = os.fspath(image_path)
        self.collision_path = os.fspath(collision_path) if collision_path else None
        self.surface = pygame.image.load(self.image_path).convert_alpha()
        self.rect = self.surface.get_rect(topleft=(0, 0))
        self.playable_bounds = pygame.Rect(self.rect)
        self.collision_rects = []
        self.collision_entries = []
        self.collision_rects_by_type = {}
        self.bounds_padding = 0
        self.collision_margin = 3.0

        if self.collision_path and os.path.exists(self.collision_path):
            self._load_collision_data(self.collision_path)

    def _load_collision_data(self, path):
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        self.bounds_padding = max(0, int(data.get("bounds_padding", 0)))
        margin = data.get("collision_margin")
        if margin is not None:
            self.collision_margin = max(0.0, float(margin))
        self.playable_bounds = self.rect.inflate(-self.bounds_padding * 2, -self.bounds_padding * 2)
        if self.playable_bounds.width < 0 or self.playable_bounds.height < 0:
            self.playable_bounds = pygame.Rect(self.rect)
        rects = data.get("rects", [])
        self.collision_rects = []
        self.collision_entries = []
        self.collision_rects_by_type = {}

        for entry in rects:
            rect_data = None
            rect_type = "interior"
            if isinstance(entry, dict):
                rect_data = entry.get("rect") or entry.get("bounds") or entry.get("value")
                rect_type = entry.get("type", rect_type)
            else:
                rect_data = entry

            if not rect_data or len(rect_data) != 4:
                continue

            rect = pygame.Rect(*rect_data)
            rect_type = str(rect_type).lower()
            if rect_type not in {"interior", "exterior"}:
                rect_type = "interior"

            self.collision_rects.append(rect)
            self.collision_entries.append((rect, rect_type))
            self.collision_rects_by_type.setdefault(rect_type, []).append(rect)

    def draw(self, screen, camera, offset):
        screen.blit(self.surface, (int(-camera.x + offset.x), int(-camera.y + offset.y)))

    def iter_collision_entries(self, collision_types=None):
        if collision_types is None:
            yield from self.collision_entries
            return

        allowed = {str(type_name).lower() for type_name in collision_types}
        for rect, rect_type in self.collision_entries:
            if rect_type in allowed:
                yield rect, rect_type

    def iter_collision_rects(self, collision_types=None):
        for rect, _ in self.iter_collision_entries(collision_types):
            yield rect

    def clamp_circle_to_bounds(self, position, radius):
        if self.playable_bounds.width <= 0 or self.playable_bounds.height <= 0:
            return
        min_x = self.playable_bounds.left + radius
        max_x = self.playable_bounds.right - radius
        min_y = self.playable_bounds.top + radius
        max_y = self.playable_bounds.bottom - radius
        if min_x > max_x:
            min_x = max_x = self.playable_bounds.centerx
        if min_y > max_y:
            min_y = max_y = self.playable_bounds.centery
        position.x = _clamp(position.x, min_x, max_x)
        position.y = _clamp(position.y, min_y, max_y)

    def resolve_collisions(self, position, radius, collision_types=None):
        effective_radius = max(0.0, radius - self.collision_margin)
        rects = list(self.iter_collision_rects(collision_types))
        for _ in range(3):
            adjusted = False
            for rect in rects:
                if _resolve_circle_rect(position, effective_radius, rect):
                    adjusted = True
            if not adjusted:
                break
        self.clamp_circle_to_bounds(position, effective_radius)


def _resolve_circle_rect(position, radius, rect):
    closest_x = _clamp(position.x, rect.left, rect.right)
    closest_y = _clamp(position.y, rect.top, rect.bottom)
    diff_x = position.x - closest_x
    diff_y = position.y - closest_y
    distance_sq = diff_x * diff_x + diff_y * diff_y
    if distance_sq == 0:
        left_pen = abs(position.x - rect.left)
        right_pen = abs(rect.right - position.x)
        top_pen = abs(position.y - rect.top)
        bottom_pen = abs(rect.bottom - position.y)
        best = (left_pen, (-1, 0))
        for candidate in ((right_pen, (1, 0)), (top_pen, (0, -1)), (bottom_pen, (0, 1))):
            if candidate[0] < best[0]:
                best = candidate
        _, axis = best
        if axis[0] != 0:
            position.x = rect.left - radius if axis[0] < 0 else rect.right + radius
        else:
            position.y = rect.top - radius if axis[1] < 0 else rect.bottom + radius
        return True

    distance = distance_sq ** 0.5
    if distance >= radius:
        return False
    if distance == 0:
        return False
    penetration = radius - distance
    norm_x = diff_x / distance
    norm_y = diff_y / distance
    position.x += norm_x * penetration
    position.y += norm_y * penetration
    return True



