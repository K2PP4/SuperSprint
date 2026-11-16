from src.lib.actor import Actor, Arena, Point
from src.lib.polar import move_around
from src.funcs import clamp, actor_center, is_in_bounds
from src.enums import Car_colors, Car_size
from math import dist, degrees, atan2
import os

class Car(Actor):
    def __init__(self, pos: tuple[int, int], color: Car_colors, player_name: str = "Default"):
        self._pos               = pos
        self._prev_pos          = pos
        self._color             = color.value
        self._player_name       = player_name
        self._size              = Car_size.dims.value

        self._speed             = 0.0
        self._acceleration      = 1.0
        self._max_speed         = 10.0
        self._min_speed         = -2.0
        self._angle             = 0.0
        self._prev_angle        = 0.0
        self._angle_debounce    = 0
        self._angle_cooldown    = 5
        self._angle_inc         = 90 / 8
        self._frame             = 0
        self._show              = True

        self._target_chkpnt_idx = 0
        self._laps              = 0
        self._tot_chkpnt_hit    = 0
        self._is_finished       = False
        self._finished_rank     = 0

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

    def advance_checkpoint(self, total_checkpoints: int):
        """
        Advances the checkpoint index and hit amount, if it completes a lap increments that as well.
        """
        self._tot_chkpnt_hit += 1
        self._target_chkpnt_idx = (self._target_chkpnt_idx + 1) % total_checkpoints
        if self._target_chkpnt_idx == 0:
            self._laps += 1

    def bounce_back(self, damp: float = 0.35):
        """
        Bounces the car back and slows it down.
        """
        self._speed = -self._speed * damp
        if abs(self._speed) < 0.2:
            self._speed = 0.0

    def move(self, arena: Arena):
        raise NotImplementedError("Abstract method implemented in child classes.")

class UsrCar(Car):
    def __init__(self, pos: Point, color: Car_colors, name: str = "Player", controls: dict = None):
        super().__init__(pos, color, name)
        self._controls = controls or {
            "up": "ArrowUp",
            "dn": "ArrowDown",
            "dx": "ArrowRight",
            "sx": "ArrowLeft"
        }

    def move(self, arena: Arena):
        if self._is_finished:
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
                 waypoints: list[Point] = None, max_speed: float = 5.0):
        super().__init__(pos, color, name)
        self._waypoints = waypoints or []
        self._current_wp_idx = 0
        self._max_speed = max_speed
        self._angle = 0.0  # Facing right (counter-clockwise on top straight)
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

    def move(self, arena: Arena = None):
        if self._is_finished:
            return

        self._frame += 1

        # If waypoints are available, steer towards target waypoint
        if self._waypoints:
            tx, ty = self._waypoints[self._current_wp_idx]
            cx, cy = self.center
            dx = tx - cx
            dy = ty - cy
            dist_to_wp = dist((cx, cy), (tx, ty))

            # Reached waypoint -> advance to next
            if dist_to_wp < 24:
                self.advance_checkpoint(len(self._waypoints))
                self._current_wp_idx = (self._current_wp_idx + 1) % len(self._waypoints)
                tx, ty = self._waypoints[self._current_wp_idx]
                dx = tx - cx
                dy = ty - cy

            desired_ang = degrees(atan2(dy, dx)) % 360
            angle_diff = (desired_ang - self._angle + 180) % 360 - 180

            # Smooth steering towards target waypoint
            if angle_diff > 2:
                self._angle = (self._angle + min(self._angle_inc, angle_diff)) % 360
            elif angle_diff < -2:
                self._angle = (self._angle + max(-self._angle_inc, angle_diff)) % 360

            # Slow down slightly in sharp curves, accelerate on straights
            if abs(angle_diff) > 20:
                self._speed = max(2.5, self._speed - 0.4)
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
                self.bounce_back()
                self._angle = (self._angle + self._angle_inc) % 360
        else:
            self._pos = move_around(self._pos, self._speed, self._angle)

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
