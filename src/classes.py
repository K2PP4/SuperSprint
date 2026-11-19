from src.lib.actor import Actor, Arena, Point, check_collision, check_overlap
from src.lib.polar import move_around
from src.lib import g2d
from src.funcs import clamp, actor_center, is_in_bounds
from src.enums import Car_colors, Car_size
from math import dist, degrees, atan2
import os
import random

SPRITE_SHEET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "super-sprint.png")
# (clip position, clip size) of the item sprites inside super-sprint.png
WRENCH_CLIP  = ((24, 160), (8, 10))
OIL_CLIP     = ((8, 160), (8, 8))

# ── Gameplay tuning ──
SPIN_FRAMES         = 30                                # duration of the oil-puddle spin, in frames
SPIN_TURNS          = 2                                 # full rotations performed during the spin
SPIN_STEP           = 360 * SPIN_TURNS / SPIN_FRAMES    # degrees per frame
SPIN_SLIDE_SPEED    = 2.0                               # minimum speed the car keeps sliding with
SPIN_FRICTION       = 0.97                              # speed multiplier per frame while spinning
BOUNCE_FRAMES       = 30                                # frames of lost control after hitting a wall
BOUNCE_MIN_SPEED    = 1.0                               # minimum rebound speed, so the bounce is always visible
BOUNCE_FRICTION     = 0.9                               # speed multiplier per frame while bouncing
DETOUR_RADIUS       = 90                                # CPU: how far it looks for a wrench/puddle to aim at
DETOUR_TIMEOUT      = 60                                # CPU: frames after which it gives up a detour
WP_JITTER           = 8                                 # CPU: random offset (px) applied to each waypoint
WP_REACH_RADIUS     = 16                                # CPU: distance (px) at which a waypoint counts as reached
STUCK_FRAMES        = 120                               # CPU: frames without leaving STUCK_RADIUS before it is reset
STUCK_RADIUS        = 12                                # CPU: px
WRENCH_SPEED_BONUS  = 0.5                               # max-speed bonus per wrench
MAX_WRENCHES        = 5                                 # wrenches beyond this are collected but give no bonus

class Car(Actor):
    # How Race counts the laps of this car:
    #   "checkpoints" = it must pass close to every waypoint, in order (fine for CPU cars)
    #   "splits"      = it must cross every full-width 'S' line of the map, in order (for humans,
    #                   who cannot follow the racing line exactly)
    tracking = "checkpoints"

    def __init__(self, pos: tuple[int, int], color: Car_colors, player_name: str = "Default",
                 angle: float = 0.0):
        self._pos               = pos
        self._prev_pos          = pos
        self._color             = color.value
        self._player_name       = player_name
        self._size              = Car_size.dims.value

        self._speed             = 0.0
        self._acceleration      = 1.0
        self._max_speed         = 10.0
        self._min_speed         = -2.0
        self._angle             = angle                 # heading in degrees (0 = right, 180 = left)
        self._prev_angle        = 0.0
        self._angle_debounce    = 0
        self._angle_cooldown    = 10
        self._angle_inc         = 90 / 8
        self._frame             = 0
        self._show              = True

        self._target_chkpnt_idx = 0
        self._laps              = 0
        self._tot_chkpnt_hit    = 0
        self._is_finished       = False
        self._finished_rank     = 0

        self._wrenches          = 0
        self._spin_frames       = 0                     # >0 while spinning on oil
        self._spin_heading      = 0.0                   # direction the car keeps sliding along
        self._on_oil            = False                 # True while touching a puddle
        self._bounce_frames     = 0                     # >0 while rebounding from a wall
        self._bounce_heading    = 0.0

    @property
    def name(self) -> str:
        return self._player_name

    @property
    def color(self) -> int:
        return self._color

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def angle(self) -> float:
        return self._angle

    @property
    def laps(self) -> int:
        return self._laps

    @property
    def target_checkpoint_index(self) -> int:
        return self._target_chkpnt_idx

    @property
    def total_checkpoints_hit(self) -> int:
        return self._tot_chkpnt_hit

    @property
    def is_finished(self) -> bool:
        return self._is_finished

    @property
    def finish_rank(self) -> int:
        return self._finished_rank

    @property
    def wrenches(self) -> int:
        return self._wrenches

    @property
    def spin_frames(self) -> int:
        return self._spin_frames

    @property
    def is_spinning(self) -> bool:
        return self._spin_frames > 0

    @property
    def is_bouncing(self) -> bool:
        return self._bounce_frames > 0

    @property
    def is_locked(self) -> bool:
        """True while the car has no control (oil spin or wall rebound)."""
        return self._spin_frames > 0 or self._bounce_frames > 0

    @property
    def center(self) -> tuple[float, float]:
        return (self._pos[0] + self._size[0] / 2.0, self._pos[1] + self._size[1] / 2.0)

    def pos(self) -> tuple[float, float]:
        return self._pos

    def size(self) -> tuple[int, int]:
        return self._size

    def get_sprite_cutout(self) -> tuple[str, tuple[int, int], tuple[int, int]]:
        """
        Returns the exact sprite cutout area for the spritesheet (super-sprint.png)
        for the car's color and rotation angles.
        """
        sprite_angle = 360 - (self._angle % 360)
        dir_index = (int(sprite_angle * 4) // 45) % 32

        dir_row, dir_col = divmod(dir_index, 8)
        color_y, color_x = divmod(self.color, 2)

        clip_x = (color_x * 8 + dir_col) * 16
        clip_y = (color_y * 4 + dir_row) * 16

        img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img", "super-sprint.png")
        return img_path, (clip_x, clip_y), self._size

    def set_race_progress(self, laps: int, next_gate: int, total_gates: int):
        """
        Race tracking (called by Race): laps completed, index of the next checkpoint/split
        of the current lap, and total gates passed since the start of the race.
        """
        self._laps = laps
        self._target_chkpnt_idx = next_gate
        self._tot_chkpnt_hit = total_gates

    def finish(self, rank: int):
        """
        Race tracking (called by Race): the car completed the race. It stops
        and no longer moves or reacts to input.
        """
        self._is_finished = True
        self._finished_rank = rank
        self._speed = 0.0
        self._spin_frames = self._bounce_frames = 0

    def bounce_back(self, damp: float = 0.35):
        """
        Wall hit: the car rebounds along its heading and loses control
        for BOUNCE_FRAMES frames.
        """
        direction = -1.0 if self._speed > 0 else 1.0
        self._speed = direction * max(abs(self._speed) * damp, BOUNCE_MIN_SPEED)
        self._bounce_frames = BOUNCE_FRAMES
        self._bounce_heading = self._angle

    def bounce_step(self, arena: Arena):
        """
        Advances the wall rebound by one frame (controls are ignored meanwhile).
        """
        self._bounce_frames -= 1
        self._speed *= BOUNCE_FRICTION
        next_pos = move_around(self._pos, self._speed, self._bounce_heading)
        if is_in_bounds(self, arena, 1, pos=next_pos):
            self._prev_pos = self._pos
            self._pos = next_pos
        else:
            self._speed = 0.0                           # backed into another wall: just stop
        if self._bounce_frames == 0:
            self._speed = 0.0

    def lock_step(self, arena: Arena):
        """
        One frame of an uncontrollable state: oil spin has priority over rebound.
        """
        if self._spin_frames > 0:
            self.spin_step(arena)
        else:
            self.bounce_step(arena)

    # ── Items: wrench and oil puddle ──

    def collect_wrench(self, wrench: "Wrench", arena: Arena):
        """
        Picks up a wrench: removes it from the arena and upgrades top speed.
        """
        arena.kill(wrench)
        if self._wrenches < MAX_WRENCHES:
            self._wrenches += 1
            self._max_speed += WRENCH_SPEED_BONUS

    def start_spin(self):
        """
        Starts the oil-puddle spin: the car loses control for SPIN_FRAMES
        frames, rotating while sliding along its previous heading.
        """
        self._spin_frames = SPIN_FRAMES
        self._spin_heading = self._angle
        self._speed = max(self._speed, SPIN_SLIDE_SPEED)

    def check_items(self, arena: Arena):
        """
        Checks contact with wrenches and oil puddles in the arena.
        """
        on_oil = False
        for a in arena.actors():
            if isinstance(a, Wrench) and check_collision(self, a):
                self.collect_wrench(a, arena)
            elif isinstance(a, OilPuddle) and check_overlap(self, a):
                on_oil = True
        # Spin only when *entering* a puddle, so a car stopped on it doesn't spin forever
        if on_oil and not self._on_oil and not self.is_spinning:
            self.start_spin()
        self._on_oil = on_oil

    def spin_step(self, arena: Arena):
        """
        Advances the spin by one frame (controls are ignored meanwhile).
        """
        self._spin_frames -= 1
        self._angle = (self._angle + SPIN_STEP) % 360
        self._speed *= SPIN_FRICTION

        next_pos = move_around(self._pos, self._speed, self._spin_heading)
        if is_in_bounds(self, arena, 1, pos=next_pos):
            self._prev_pos = self._pos
            self._pos = next_pos
        else:
            self._speed = -self._speed * 0.35           # slide rebounds, no extra lock

        if self._spin_frames == 0:
            self._angle = self._spin_heading % 360

    def move(self, arena: Arena):
        raise NotImplementedError("Abstract method implemented in child classes.")

class UsrCar(Car):
    tracking = "splits"                                 # human driver: laps are counted with the map's split lines

    def __init__(self, pos: Point, color: Car_colors, name: str = "Player", controls: dict = None,
                 angle: float = 0.0):
        super().__init__(pos, color, name, angle)
        self._controls = controls or {
            "up": "ArrowUp",
            "dn": "ArrowDown",
            "dx": "ArrowRight",
            "sx": "ArrowLeft"
        }

    def move(self, arena: Arena):
        if self._is_finished:
            return

        self.check_items(arena)
        if self.is_locked:
            self.lock_step(arena)
            return

        keys = arena.current_keys()

        accelerating = self._controls["up"] in keys
        braking = self._controls["dn"] in keys
        turning_left = self._controls["sx"] in keys
        turning_right = self._controls["dx"] in keys

        if accelerating:
            self._speed = clamp(self._speed + self._acceleration, self._min_speed, self._max_speed)
        elif braking:
            self._speed = clamp(self._speed - self._acceleration, self._min_speed, self._max_speed)

        # Allow turning even when stopped
        turn_mult = 1.0 if self._speed >= 0 else -1.0
        if self._angle_cooldown > 0:
            self._angle_cooldown -= 1
        elif self._angle_cooldown == 0:
            if turning_left:
                self._angle = (self._angle - self._angle_inc * turn_mult) % 360
                self._angle_cooldown = self._angle_debounce
            elif turning_right:
                self._angle = (self._angle + self._angle_inc * turn_mult) % 360
                self._angle_cooldown = self._angle_debounce

        # Recovery safeguard: if currently out of bounds, restore prev_pos if valid
        if not is_in_bounds(self, arena, 1, pos=self._pos):
            if is_in_bounds(self, arena, 1, pos=self._prev_pos):
                self._pos = self._prev_pos

        # Prospective movement check
        if self._speed != 0:
            next_pos = move_around(self._pos, self._speed, self._angle)
            if is_in_bounds(self, arena, 1, pos=next_pos):
                self._prev_pos = self._pos
                self._pos = next_pos
            else:
                self.bounce_back()

class CpuCar(Car):
    def __init__(self, pos: Point, color: Car_colors, name: str = "CPU",
                 waypoints: list[Point] = None, max_speed: float = 5.0,
                 wrench_chance: float = 0.7, oil_chance: float = 0.1, seed: int = None,
                 angle: float = 0.0):
        super().__init__(pos, color, name, angle)
        self._waypoints = waypoints or []
        self._current_wp_idx = 0
        # "Human error" model: each time the CPU picks a new waypoint it may aim
        # at a nearby wrench (wrench_chance) or, by mistake, at a puddle (oil_chance).
        self._wrench_chance = wrench_chance
        self._oil_chance = oil_chance
        self._rng = random.Random(seed)
        self._wp_offset = (0.0, 0.0)
        self._detour_item = None
        self._detour_age = 0
        # Stuck detection: if the car stays near the same spot for too long, reset it
        self._anchor_pos = pos
        self._anchor_frames = 0
        self._max_speed = max_speed
        self._speed = 0.0

    @property
    def waypoints(self) -> list[Point]:
        return self._waypoints

    @waypoints.setter
    def waypoints(self, wps: list[Point]):
        self._waypoints = wps

    @property
    def current_waypoint_index(self) -> int:
        return self._current_wp_idx

    def _roll_target(self, arena: Arena):
        """
        Called on each new waypoint: jitters the racing line and randomly
        decides whether to detour towards a wrench (good) or a puddle (mistake).
        """
        # Random offset, but only if a car-sized box centered there (and slightly
        # further out) is still on the track; otherwise keep the exact waypoint.
        self._wp_offset = (0.0, 0.0)
        if arena is not None and self._waypoints:
            wx, wy = self._waypoints[self._current_wp_idx]
            hw, hh = self._size[0] / 2, self._size[1] / 2
            for _ in range(4):
                ox = self._rng.uniform(-WP_JITTER, WP_JITTER)
                oy = self._rng.uniform(-WP_JITTER, WP_JITTER)
                if (is_in_bounds(self, arena, 1, pos=(wx + ox - hw, wy + oy - hh))
                        and is_in_bounds(self, arena, 1, pos=(wx + ox * 1.5 - hw, wy + oy * 1.5 - hh))):
                    self._wp_offset = (ox, oy)
                    break
        self._detour_item = None
        self._detour_age = 0
        if arena is None:
            return

        def candidates(kind):
            found = []
            for a in arena.actors():
                if not isinstance(a, kind):
                    continue
                ax, ay = actor_center(a)
                cx, cy = self.center
                if dist((cx, cy), (ax, ay)) > DETOUR_RADIUS:
                    continue
                ang = degrees(atan2(ay - cy, ax - cx)) % 360
                if abs((ang - self._angle + 180) % 360 - 180) < 100:  # roughly ahead
                    found.append((dist((cx, cy), (ax, ay)), a))
            return min(found, key=lambda t: t[0])[1] if found else None

        wrench, oil = candidates(Wrench), candidates(OilPuddle)
        if wrench and self._rng.random() < self._wrench_chance:
            self._detour_item = wrench
        elif oil and self._rng.random() < self._oil_chance:
            self._detour_item = oil

    def _target(self, arena: Arena) -> Point:
        """
        Current steering target: detour item if any, else the jittered waypoint.
        """
        item = self._detour_item
        if item is not None:
            self._detour_age += 1
            if (arena is None or item not in arena.actors()
                    or self._detour_age > DETOUR_TIMEOUT):
                self._detour_item = None
            else:
                return actor_center(item)
        wx, wy = self._waypoints[self._current_wp_idx]
        return (wx + self._wp_offset[0], wy + self._wp_offset[1])

    def _recover_if_stuck(self):
        """
        Safety net: if the car has not left a small area for STUCK_FRAMES frames,
        put it back on the previous waypoint, facing the current target.
        """
        if not self._waypoints:
            return
        if dist(self._pos, self._anchor_pos) > STUCK_RADIUS:
            self._anchor_pos = self._pos
            self._anchor_frames = 0
            return
        self._anchor_frames += 1
        if self._anchor_frames < STUCK_FRAMES:
            return
        px, py = self._waypoints[self._current_wp_idx - 1]
        tx, ty = self._waypoints[self._current_wp_idx]
        self._pos = (px - self._size[0] / 2, py - self._size[1] / 2)
        self._prev_pos = self._pos
        self._angle = degrees(atan2(ty - py, tx - px)) % 360
        self._speed = 0.0
        self._spin_frames = self._bounce_frames = 0
        self._detour_item = None
        self._anchor_pos = self._pos
        self._anchor_frames = 0

    def move(self, arena: Arena = None):
        if self._is_finished:
            return

        self._recover_if_stuck()

        if arena is not None:
            self.check_items(arena)
            if self.is_locked:
                self.lock_step(arena)
                return

        self._frame += 1

        # If waypoints are available, steer towards target waypoint
        if self._waypoints:
            cx, cy = self.center

            # Reached waypoint -> advance to next, and re-roll the target
            # (lap/checkpoint counting is done by Race, not here)
            if dist((cx, cy), self._waypoints[self._current_wp_idx]) < WP_REACH_RADIUS:
                self._current_wp_idx = (self._current_wp_idx + 1) % len(self._waypoints)
                self._roll_target(arena)

            tx, ty = self._target(arena)
            dx = tx - cx
            dy = ty - cy

            desired_ang = degrees(atan2(dy, dx)) % 360
            angle_diff = (desired_ang - self._angle + 180) % 360 - 180

            # Smooth steering towards target waypoint
            if angle_diff > 2:
                self._angle = (self._angle + min(self._angle_inc, angle_diff)) % 360
            elif angle_diff < -2:
                self._angle = (self._angle + max(-self._angle_inc, angle_diff)) % 360

            # Slow down in sharp curves (almost stopping if badly misaligned, so the car
            # can turn first instead of driving into the wall), accelerate on straights
            if abs(angle_diff) > 20:
                self._speed = max(1.0, self._speed - 0.4)
            else:
                self._speed = min(self._max_speed, self._speed + 0.3)
        else:
            # Fallback simple wandering if no waypoints
            if self._frame % 64 == 0:
                self._angle_inc *= -1
            if self._frame % 2 == 0:
                self._angle = (self._angle + self._angle_inc) % 360

        # Move with collision check
        if arena is not None and self._speed != 0:
            next_pos = move_around(self._pos, self._speed, self._angle)
            if is_in_bounds(self, arena, 1, pos=next_pos):
                self._prev_pos = self._pos
                self._pos = next_pos
            else:
                # Wall hit: rebound and lose control; steering resumes afterwards
                self.bounce_back()
        else:
            self._pos = move_around(self._pos, self._speed, self._angle)

class Item(Actor):
    """
    Static pickup/hazard placed on the track. Built from the center of its map tile.
    """
    def __init__(self, center: Point, size: Point, clip: tuple):
        w, h = size
        self._size = size
        self._pos = (center[0] - w / 2, center[1] - h / 2)
        self._clip_pos, self._clip_size = clip          # sprite area in super-sprint.png

    def move(self, arena: Arena):
        pass

    def pos(self) -> Point:
        return self._pos

    def size(self) -> Point:
        return self._size

    def sprite(self) -> Point | None:
        return None

    def draw(self):
        # sprite centered on the hitbox
        w, h = self._size
        cw, ch = self._clip_size
        x = self._pos[0] + (w - cw) / 2
        y = self._pos[1] + (h - ch) / 2
        g2d.draw_image(SPRITE_SHEET, (x, y), self._clip_pos, self._clip_size)

class Wrench(Item):
    """
    Collected by cars ('w' in the map): each one upgrades the car's top speed.
    """
    def __init__(self, center: Point):
        super().__init__(center, (12, 12), WRENCH_CLIP)

class OilPuddle(Item):
    """
    Hazard ('p' in the map): cars touching it spin out for SPIN_FRAMES frames.
    """
    def __init__(self, center: Point):
        super().__init__(center, (10, 10), OIL_CLIP)

class CurvedWall(Actor):
    def __init__(self, pos: Point, size: Point, center: Point, radius: float):
        self._pos = pos
        self._size = size
        self._center = center
        self._radius = radius

    def move(self, arena: Arena):
        pass

    def pos(self) -> Point:
        return self._pos

    def size(self) -> Point:
        return self._size

    def sprite(self) -> Point | None:
        return None

    def center(self) -> Point:
        return self._center

    def radius(self) -> float:
        return self._radius

class ExternalWall(CurvedWall):
    def confirm_collision(self, other: Actor) -> bool:
        return dist(self.center(), actor_center(other)) > self._radius

class InternalWall(CurvedWall):
    def confirm_collision(self, other: Actor) -> bool:
        return dist(self.center(), actor_center(other)) < self._radius
