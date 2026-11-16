from src.lib.actor import Arena, Actor, Point
from src.lib import g2d
from src.enums import Arena_size
import os

_walls_cache: dict[int, list[str]] = {}

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

def get_cached_walls(lvl: int = 1) -> list[str]:
    if lvl not in _walls_cache:
        wall_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps", f"lvl-{lvl}.txt")
        _walls_cache[lvl] = load_walls(wall_dir)
    return _walls_cache[lvl]

def is_wall(x, y, walls: list[str]) -> bool:
    iy, ix = int(y), int(x)
    if 0 <= iy < len(walls) and 0 <= ix < len(walls[iy]):
        return walls[iy][ix] == "#"
    return True

def wall_pos(center: Point, walls: list[str]) -> Point | None:
    K = 8
    xc, yc = center
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

def draw_walls(walls: list[str] = None, lvl: int = 1, tile_size: int = 8, color: tuple = (255, 0, 0, 90), width: int = 0):
    if walls is None:
        walls = get_cached_walls(lvl)
    g2d.set_color(color, width)
    for r, row in enumerate(walls):
        for c, ch in enumerate(row):
            if ch == "#":
                g2d.draw_rect((c * tile_size, r * tile_size), (tile_size, tile_size))

def is_in_bounds(actor: Actor, arena: Arena, lvl: int = 1, pos: Point = None, walls: list[str] = None) -> bool:
    if pos is None:
        pos = actor.pos()
    x, y = pos
    carw, carh = actor.size()
    arenaw, arenah = arena.size()

    margin = 2
    if x + margin < 0 or y + margin < 0 or x + carw - margin > arenaw or y + carh - margin > arenah:
        return False

    if walls is None:
        walls = get_cached_walls(lvl)

    K = 8
    col_start = int((x + margin) // K)
    col_end = int((x + carw - 1 - margin) // K)
    row_start = int((y + margin) // K)
    row_end = int((y + carh - 1 - margin) // K)

    for r in range(row_start, row_end + 1):
        for c in range(col_start, col_end + 1):
            if is_wall(c, r, walls):
                return False

    return True

def draw_actor(actor: Actor):
    img_path, clip_loc, clip_size = actor.get_sprite_cutout()
    g2d.draw_image(img_path, actor.pos(), clip_loc, clip_size)

def init_arena(lvl: int = 1, size: tuple[int, int] = Arena_size.dims.value):
    img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "super-sprint-bg.png")
    track_idx = (lvl - 1) % 8
    row, col = divmod(track_idx, 4)
    clip_x = col * 514
    clip_y = row * 482
    g2d.draw_image(img_path, (0, 0), (clip_x, clip_y), size)

def draw_debug_info(car: Actor, lvl: int = 1):
    # 1. Draw walls overlay
    draw_walls(lvl=lvl, color=(255, 0, 0, 80))

    # 2. Draw car bounding box (with margin)
    x, y = car.pos()
    w, h = car.size()
    margin = 2
    g2d.set_color((0, 255, 0, 220), width=1)
    g2d.draw_rect((x + margin, y + margin), (w - 2 * margin, h - 2 * margin))

    # 3. Draw telemetry text banner
    col = int((x + w / 2) // 8)
    row = int((y + h / 2) // 8)
    speed = getattr(car, "speed", 0.0)
    angle = getattr(car, "angle", 0.0)
    info_text = f"DEBUG [W] | Pos: ({int(x)}, {int(y)}) | Tile: ({col}, {row}) | Spd: {speed:.1f} | Ang: {int(angle)}deg"
    g2d.set_color((0, 0, 0, 180), width=0)
    g2d.draw_rect((4, 4), (len(info_text) * 7 + 10, 18))
    g2d.set_color((255, 255, 255), width=0)
    g2d.draw_text(info_text, (len(info_text) * 3.5 + 8, 13), 14)
