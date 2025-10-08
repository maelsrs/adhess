from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pygame

DirectionFrames = List[List[pygame.Surface]]


def load_directional_frames(
    root: Path,
    prefix: str,
    frame_count: int,
    frames_per_direction: int,
    scale: float = 1.0,
    direction_order: Optional[List[int]] = None,
) -> DirectionFrames:
    frames: List[pygame.Surface] = []
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


def build_idle_frames(walk_frames: DirectionFrames) -> DirectionFrames:
    idle: DirectionFrames = []
    for direction_frames in walk_frames:
        idle.append([direction_frames[0]] if direction_frames else [])
    return idle


class AnimationSet:
    def __init__(self, data: Dict[str, Dict]):
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

    def frame(self, direction: int):
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
