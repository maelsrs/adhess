import pygame


def vector_to_direction_index(vector):
    if vector.length_squared() == 0:
        return 0
    x, y = vector.x, vector.y
    if abs(x) > abs(y):
        return 2 if x > 0 else 1
    return 0 if y >= 0 else 3
