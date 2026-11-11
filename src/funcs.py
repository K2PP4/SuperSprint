from lib.actor import Actor, Point

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