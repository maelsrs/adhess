import json
from pathlib import Path

import pygame

from adhess.entities.enemy import Enemy


DEFAULT_PATH = Path("savegame.json")


def vector_to_list(vector):
    if vector is None:
        return [0.0, 0.0]
    return [float(vector.x), float(vector.y)]


def vector_from_list(value, fallback=None):
    if value is None:
        base = fallback if fallback is not None else (0.0, 0.0)
        return pygame.Vector2(base)
    data = list(value)
    if len(data) < 2:
        base = fallback if fallback is not None else (0.0, 0.0)
        return pygame.Vector2(base)
    return pygame.Vector2(float(data[0]), float(data[1]))


def state_data(game):
    return {
        "state": game.state,
        "wave": int(game.wave),
        "wave_active": bool(game.wave_active),
        "wave_delay": float(game.wave_delay),
        "wave_timer": float(game.wave_timer),
        "spawn_radius_min": float(game.spawn_radius_min),
        "spawn_radius_max": float(game.spawn_radius_max),
        "enemy_radius": float(getattr(game, "enemy_radius", 0.0)),
        "debug_show_collisions": bool(game.debug_show_collisions),
    }


def player_data(player):
    return {
        "position": vector_to_list(player.position),
        "direction": vector_to_list(player.direction),
        "radius": float(player.radius),
        "speed": float(player.speed),
        "max_health": float(player.max_health),
        "health": float(player.health),
        "attack": {
            "reach": float(player.attack_reach),
            "radius": float(player.attack_radius),
            "damage": float(player.attack_damage),
            "duration": float(player.attack_duration),
            "cooldown_time": float(player.attack_cooldown_time),
        },
        "dash": {
            "speed": float(player.dash_speed),
            "duration": float(player.dash_duration),
            "cooldown_time": float(player.dash_cooldown_time),
        },
    }


def enemy_data(enemy):
    return {
        "position": vector_to_list(enemy.position),
        "direction": vector_to_list(enemy.direction),
        "radius": float(enemy.radius),
        "speed": float(enemy.speed),
        "max_health": float(enemy.max_health),
        "health": float(enemy.health),
        "attack_damage": float(enemy.attack_damage),
        "attack_cooldown_time": float(enemy.attack_cooldown_time),
        "attack_duration": float(enemy.attack_duration),
    }


def bindings_data(game):
    mapping = {action: [int(k) for k in keys] for action, keys in game.key_bindings.items()}
    data = {}
    if mapping:
        data["key_bindings"] = mapping
    if getattr(game, "binding_menu_key", None) is not None:
        data["binding_menu_key"] = int(game.binding_menu_key)
    return data


def to_data(game):
    data = {
        "state": state_data(game),
        "player": player_data(game.player),
        "enemies": [enemy_data(e) for e in game.enemies],
        "camera": vector_to_list(game.camera),
    }
    b = bindings_data(game)
    if b:
        data["bindings"] = b
    return data


def set_state(game, data):
    if not data:
        return
    game.state = data.get("state", game.state)
    game.wave = int(data.get("wave", game.wave))
    game.wave_active = bool(data.get("wave_active", game.wave_active))
    game.wave_delay = float(data.get("wave_delay", game.wave_delay))
    game.wave_timer = float(data.get("wave_timer", game.wave_timer))
    game.spawn_radius_min = float(data.get("spawn_radius_min", game.spawn_radius_min))
    game.spawn_radius_max = float(data.get("spawn_radius_max", game.spawn_radius_max))
    enemy_radius = data.get("enemy_radius")
    if enemy_radius is not None:
        game.enemy_radius = float(enemy_radius)
    game.debug_show_collisions = bool(data.get("debug_show_collisions", game.debug_show_collisions))


def set_player(player, data):
    if not data:
        return
    player.position = vector_from_list(data.get("position"), player.position)
    player.direction = vector_from_list(data.get("direction"), player.direction)

    radius = data.get("radius")
    if radius is not None:
        player.radius = float(radius)

    speed = data.get("speed")
    if speed is not None:
        player.speed = float(speed)

    max_health = data.get("max_health")
    if max_health is not None:
        player.max_health = float(max_health)

    health = data.get("health")
    if health is not None:
        player.health = min(player.max_health, float(health))

    attack = data.get("attack", {})
    value = attack.get("reach")
    if value is not None:
        player.attack_reach = float(value)
    value = attack.get("radius")
    if value is not None:
        player.attack_radius = float(value)
    value = attack.get("damage")
    if value is not None:
        player.attack_damage = float(value)
    value = attack.get("duration")
    if value is not None:
        player.attack_duration = float(value)
    cooldown_time = attack.get("cooldown_time")
    if cooldown_time is not None:
        player.attack_cooldown_time = float(cooldown_time)
        player.attack_cooldown = min(player.attack_cooldown, player.attack_cooldown_time)

    dash = data.get("dash", {})
    value = dash.get("speed")
    if value is not None:
        player.dash_speed = float(value)
    value = dash.get("duration")
    if value is not None:
        player.dash_duration = float(value)
    cooldown_time = dash.get("cooldown_time")
    if cooldown_time is not None:
        player.dash_cooldown_time = float(cooldown_time)
        player.dash_cooldown = min(player.dash_cooldown, player.dash_cooldown_time)


def set_enemies(game, enemies_data):
    enemies = []
    for entry in enemies_data or []:
        position = vector_from_list(entry.get("position"))
        radius = float(entry.get("radius", getattr(game, "enemy_radius", 10.0)))
        enemy = Enemy(position, game.clone_enemy_animation(), radius)
        enemy.direction = vector_from_list(entry.get("direction"), enemy.direction)

        for attr in ("speed", "max_health", "health", "attack_damage"):
            value = entry.get(attr)
            if value is not None:
                setattr(enemy, attr, float(value))

        cooldown_time = entry.get("attack_cooldown_time")
        if cooldown_time is not None:
            enemy.attack_cooldown_time = float(cooldown_time)
            enemy.attack_timer = min(enemy.attack_timer, enemy.attack_cooldown_time)

        duration = entry.get("attack_duration")
        if duration is not None:
            enemy.attack_duration = float(duration)

        enemies.append(enemy)
    game.enemies = enemies


def set_bindings(game, data):
    if not data:
        return
    key_bindings = data.get("key_bindings")
    if key_bindings is not None:
        game.key_bindings = {action: [int(k) for k in keys] for action, keys in key_bindings.items()}
    binding_menu_key = data.get("binding_menu_key")
    if binding_menu_key is not None:
        game.binding_menu_key = int(binding_menu_key)


def from_data(game, payload):
    set_state(game, payload.get("state", {}))
    set_player(game.player, payload.get("player", {}))
    set_enemies(game, payload.get("enemies", []))
    set_bindings(game, payload.get("bindings"))
    camera_data = payload.get("camera")
    if camera_data is not None:
        game.camera = vector_from_list(camera_data, game.camera)


def save_game(game, path=None):
    target = Path(path) if path is not None else DEFAULT_PATH
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(to_data(game), f, indent=2)
    return target


def load_game(game, path=None):
    target = Path(path) if path is not None else DEFAULT_PATH
    with target.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    from_data(game, payload)
    return payload


def has_save(path=None):
    target = Path(path) if path is not None else DEFAULT_PATH
    return target.exists() and target.is_file()

