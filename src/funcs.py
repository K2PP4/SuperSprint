from src.lib.actor import Arena, Actor, Point
from src.lib import g2d
from src.enums import Arena_size
import os

_walls_cache: dict[int, list[str]] = {}

# Map characters that are drivable (not walls):
#   ' ' track, '@' waypoint, 'F' finish line, 'S' split, 'w' wrench, 'p' oil puddle
_FREE_TILES = (" ", "@", "F", "S", "w", "p")

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
        ch = walls[iy][ix]
        return ch not in _FREE_TILES
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

def load_items(lvl: int, marker: str) -> list[Point]:
    """
    Returns the pixel centers (x, y) of every tile marked with `marker`
    in maps/lvl-{lvl}.txt (e.g. 'w' = wrench, 'p' = oil puddle).
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps", f"lvl-{lvl}.txt")
    centers = []
    if os.path.exists(path):
        with open(path) as f:
            for r, line in enumerate(f):
                for c, ch in enumerate(line.rstrip("\n")):
                    if ch == marker:
                        centers.append((c * 8 + 4, r * 8 + 4))
    return centers

def load_waypoints(lvl: int = 1, start_pos: tuple = None, start_heading: tuple = None) -> list[Point]:
    """
    Extracts and orders waypoints marked with '@' from maps/lvl-{lvl}.txt.
    Returns pixel coordinates (x, y) along the racing line (counter-clockwise on screen).
    start_pos: pixel position of the starting grid (default: just right of the FL, on the top straight).
    start_heading: initial direction as (dx, dy) unit vector (default: (-1,0) = left,
    which is counter-clockwise along the top straight).
    """
    raw_wps = load_items(lvl, "@")

    if not raw_wps:
        return []

    # Default: start behind the finish line (to its right), heading LEFT (counter-clockwise)
    if start_pos is None:
        start_pos = (264, 92)
    if start_heading is None:
        start_heading = (-1.0, 0.0)

    # Find first waypoint ahead of start position along the heading direction
    scored = []
    for p in raw_wps:
        dx = p[0] - start_pos[0]
        dy = p[1] - start_pos[1]
        d = (dx ** 2 + dy ** 2) ** 0.5
        if d > 0:
            dot = (dx * start_heading[0] + dy * start_heading[1]) / d
            if dot > 0.3:                               # Waypoint is roughly ahead
                scored.append((d * (2.0 - dot), p))
    scored.sort(key=lambda x: x[0])
    first_wp = scored[0][1] if scored else raw_wps[0]

    ordered = [first_wp]
    remaining = set(raw_wps)
    remaining.discard(first_wp)

    curr = first_wp
    heading = start_heading

    while remaining:
        best_p = None
        best_score = float("inf")
        for p in remaining:
            dx = p[0] - curr[0]
            dy = p[1] - curr[1]
            d = (dx ** 2 + dy ** 2) ** 0.5
            if d > 0:
                dot = (dx * heading[0] + dy * heading[1]) / d
                score = d * (2.0 - dot) if dot > -0.3 else d * 10.0
                if score < best_score:
                    best_score = score
                    best_p = p
        if best_p is None:
            break
        ordered.append(best_p)
        remaining.discard(best_p)
        dx = best_p[0] - curr[0]
        dy = best_p[1] - curr[1]
        d = (dx ** 2 + dy ** 2) ** 0.5
        if d > 0:
            heading = (dx / d, dy / d)
        curr = best_p

    return ordered

def load_finish_line(lvl: int = 1) -> list[Point]:
    """
    Reads 'F' markers from maps/lvl-{lvl}.txt and returns the pixel rectangles
    forming the finish line. Returns list of (x, y) pixel positions (top-left of each 8x8 tile).
    """
    return [(cx - 4, cy - 4) for cx, cy in load_items(lvl, "F")]

def load_marked_groups(lvl: int, marker: str) -> list[tuple[int, int, int, int]]:
    """
    Finds the groups of adjacent `marker` tiles in maps/lvl-{lvl}.txt (e.g. one group
    per finish line 'F' or per split 'S', drawn as a row/column of tiles across the road).
    Returns one tile bounding box (col_min, row_min, col_max, row_max) per group.
    """
    walls = get_cached_walls(lvl)
    todo = {(c, r) for r, row in enumerate(walls) for c, ch in enumerate(row) if ch == marker}
    groups = []
    while todo:
        stack = [todo.pop()]
        cols, rows = [], []
        while stack:
            c, r = stack.pop()
            cols.append(c)
            rows.append(r)
            for n in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                if n in todo:
                    todo.remove(n)
                    stack.append(n)
        groups.append((min(cols), min(rows), max(cols), max(rows)))
    return sorted(groups, key=lambda g: (g[1], g[0]))

class Gate:
    """
    A line drawn across the WHOLE road in the map: 'F' = finish line, 'S' = split.
    A car crosses it by driving over the line, so (unlike a small checkpoint circle)
    it cannot be missed. The race direction is read from the waypoint path, so the
    same class handles vertical lines (a column of tiles) and horizontal ones (a row).
    """
    def __init__(self, box: tuple[int, int, int, int], racing_line: list[Point]):
        c0, r0, c1, r1 = box
        self.vertical = (r1 - r0) >= (c1 - c0)          # a column of tiles = vertical line
        if self.vertical:
            self.line = c0 * 8 + 4                      # x of the line (middle of the tile)
            self.lo, self.hi = r0 * 8, (r1 + 1) * 8     # y extent of the line
        else:
            self.line = r0 * 8 + 4                      # y of the line (middle of the tile)
            self.lo, self.hi = c0 * 8, (c1 + 1) * 8     # x extent of the line
        self.sign, self.order = self._direction(racing_line)

    def _across(self, pt: Point) -> float:
        """Coordinate of `pt` perpendicular to the line (the one that changes when crossing)."""
        return pt[0] if self.vertical else pt[1]

    def _along(self, pt: Point) -> float:
        """Coordinate of `pt` along the line."""
        return pt[1] if self.vertical else pt[0]

    def _direction(self, racing_line: list[Point]) -> tuple[int, float]:
        """
        Finds where the waypoint path crosses the line. Returns (sign, order):
        sign = +1/-1 is the direction of the race across the line (increasing or
        decreasing coordinate), order = position of the line along the path.
        """
        n = len(racing_line)
        for k in range(n):
            a, b = racing_line[k], racing_line[(k + 1) % n]
            pa, pb = self._across(a), self._across(b)
            if pa == pb or (pa - self.line) * (pb - self.line) > 0:
                continue                                # this segment does not reach the line
            t = (self.line - pa) / (pb - pa)
            along = self._along(a) + t * (self._along(b) - self._along(a))
            if self.lo <= along < self.hi:
                return (1 if pb > pa else -1), k + t
        raise ValueError("A finish/split line is not crossed by the waypoint path: check the map")

    def crossing(self, p: Point, q: Point) -> int:
        """
        Movement from p to q: +1 if it crosses the line in the race direction, -1 if it
        crosses it backwards, 0 if it does not cross it (or crosses outside of the road).
        """
        a, b = self._across(p), self._across(q)
        before, after = (a - self.line) * self.sign, (b - self.line) * self.sign
        if before < 0 <= after:
            way = 1
        elif after < 0 <= before:
            way = -1
        else:
            return 0
        t = (self.line - a) / (b - a)                   # where, between p and q, the line is hit
        along = self._along(p) + t * (self._along(q) - self._along(p))
        return way if self.lo <= along < self.hi else 0

def load_gates(lvl: int, racing_line: list[Point]) -> tuple[Gate, list[Gate]]:
    """
    Reads the finish line ('F') and the splits ('S') from maps/lvl-{lvl}.txt.
    Each one is a row/column of tiles across the whole road. Returns (finish, splits),
    with the splits sorted in lap order (the first one met after the finish line first).
    racing_line: ordered waypoints, used to find the direction of the race.
    """
    finish_boxes = load_marked_groups(lvl, "F")
    if len(finish_boxes) != 1:
        raise ValueError(f"The map needs exactly one finish line 'F', found {len(finish_boxes)}")
    finish = Gate(finish_boxes[0], racing_line)
    splits = [Gate(box, racing_line) for box in load_marked_groups(lvl, "S")]
    splits.sort(key=lambda g: (g.order - finish.order) % len(racing_line))
    return finish, splits

def draw_actor(actor: Actor):
    # Cars use the spritesheet; items (wrench, oil) draw themselves.
    if hasattr(actor, "get_sprite_cutout"):
        img_path, clip_loc, clip_size = actor.get_sprite_cutout()
        g2d.draw_image(img_path, actor.pos(), clip_loc, clip_size)
    elif hasattr(actor, "draw"):
        actor.draw()

def init_arena(lvl: int = 1, size: tuple[int, int] = Arena_size.dims.value):
    img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "super-sprint-bg.png")
    track_idx = (lvl - 1) % 8
    row, col = divmod(track_idx, 4)
    clip_x = col * 514
    clip_y = row * 482
    g2d.draw_image(img_path, (0, 0), (clip_x, clip_y), size)