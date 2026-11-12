from lib.actor import Actor, Arena, Point
from lib.polar import move_around
from math import dist
from funcs import clamp, actor_center
from enums import Car_colors, Car_size

class Car(Actor):
    def __init__(self, pos: tuple[int, int], color: Car_colors, player_name: Str = "Default"):
        self._pos               = pos
        self._prev_pos          = pos
        self._color             = color.value
        self._player_name       = player_name
        self._size              = Car_size.dims.value

        # TODO Parametrizzare valori?
        self._speed             = 4
        self._angle             = 0.0
        self._prev_angle        = 0.0
        self._angle_inc         = 90/8
        self._frame             = 0

        self._target_chkpnt_idx = 0
        self._laps              = 0
        self._tot_chkpnt_hit    = 0
        self._is_finished       = False
        self._finished_rank     = 0

    @property
    def name(self) -> str:
        return self._player_name

    @property
    def color(self) -> Car_colors:
        return self._color

    @property
    def speed(self) -> int:
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
        return self.is_finished

    @property
    def finish_rank(self) -> int:
        return self._finished_rank

    @property
    def center(self) -> tuple[int, int]:
        return(self._pos[0] + self._size[0] // 2, self._pos[1] + self._size[1] / 2.0)

    @property
    def pos(self) -> tuple[int, int]:
        return self._pos

    @property
    def size(self) -> tuple[int, int]:
        return self._size
    
    def get_sprite_cutout(self) -> tuple[str, tuple[int, int], tuple[int, int]]:
        """
        Returns the exact sprite cutout area for the spritesheet (super-sprint.png)
        for the car's color and rotation angles.
        """
        sprite_angle = 360 - (self._angle % 360)
        dir_index = (int(sprite_angle * 4) // 45) % 32
        
        dir_col, dir_row = divmod(dir_index, 8)

        color_x, color_y = divmod(self._color, 2)

        clip_x = (color_x * 8 + dir_col) * 16
        clip_y = (color_y * 4 + dir_row) * 16

        return "super-sprint.png", (clip_x, clip_y), self._size

    def advance_checkpoint(self, total_checkpoints: int):
        """
        Advances the checkpoint index and hit amount, if it completes a lap increments that as well.
        """
        self._tot_chkpnt_hit += 1
        self._target_chkpnt_idx = (self._target_chkpnt_idx + 1) % total_checkpoints
        if self._target_chkpnt_idx == 0 : self._laps += 1

    def bounce_back(self, damp: float = 0.35):
        """
        Bounces the car back and slows it down.
        """
        self._pos = self._prev_pos
        self._speed = -self._speed * damp

    def move(self):
        raise NotImplementedError("Abstract method implemented in child classes.")
    

class CpuCar(Car): # TODO implementare funzioni per auto CPU
    def move(self):
        self._frame += 1

        if self._frame % 64 == 0:
            self._angle_inc *= -1

        if self._frame % 2 == 0:
            self._angle = (self._angle + self._angle_inc) % 360

        self._pos = move_around(self._pos, self._speed, self._angle)

class UsrCar(Car): # TODO implementare funzioni per auto USR
    def move(self):
        self._frame += 1

        if self._frame % 64 == 0:
            self._angle_inc *= -1

        if self._frame % 2 == 0:
            self._angle = (self._angle + self._angle_inc) % 360

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
        return dist(self._center(), actor_center(other)) > self._radius

class InternalWall(CurvedWall):
    def confirm_collision(self, other: Actor) -> bool:
        return dist(self._center(), actor_center(other)) < self._radius

