from src.lib.actor import Actor, Point
from src.lib import g2d

def clamp(x, min_val, max_val):
    return max(min_val, min(x, max_val))

def actor_center(a: Actor) -> Point:
    x, y, w, h = a.pos() + a.size()
    return (x + w / 2, y + h / 2)

def load_walls(filename: str) -> list[str]:
    walls = []
    with open(filename) as file:
        for line in file:
            walls.append(line.strip())
    return walls

def is_wall(x, y, walls) -> bool:
    return walls[int(y)][int(x)] == "#"

def wall_pos(center: Point, walls: list[str]) -> Point | None:
    K = 8
    xc, xy = center
    x, y = int(xc // K), int(yc // K)
    if not is_wall(x, y, walls):
        return None
    xw, yw, n = 0, 0, 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if is_wall(x + dx, y + dy, walls):
                xw += x + dx
                yw += y + dy
                n += 1
    return (xw * K / n + K / 2, yw * K / n + K / 2)

def draw_actor(actor: Actor):
    img_path, clip_loc, clip_size = actor.get_sprite_cutout()
    g2d.draw_image(img_path, actor.pos(), clip_loc, clip_size)