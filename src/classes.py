from lib.actor import Actor, Arena, Point
from lib.polar import move_around
from math import dist
from funcs import clamp, actor_center
from enums import Car_colors, Car_size

class Car(Actor):
    def __init__(self, pos: tuple[int, int], color: Car_colors):
        self._pos       = pos
        self._color     = color.value
        self._size      = Car_size.dims.value
        self._speed     = 4
        self._angle     = 0.0
        self._angle_inc = 90/8
        self._frame     = 0

    def move(self):
        self._frame += 1

        if self._frame % 64 == 0:
            self._angle_inc *= -1

        if self._frame % 2 == 0:
            self._angle = (self._angle + self._angle_inc) % 360

        self._pos = move_around(self._pos, self._speed, self._angle)
    
    def pos(self):
        return self._pos
    
    def sprite(self) -> tuple[str, tuple[int, int], tuple[int, int]]:
        sprite_angle = 360 - (self._angle % 360)
        dir_index = (int(sprite_angle * 4) // 45) % 32
        
        dir_col, dir_row = divmod(dir_index, 8)

        color_x, color_y = divmod(self._color, 2)

        clip_x = (color_x * 8 + dir_col) * 16
        clip_y = (color_y * 4 + dir_row) * 16

        return "super-sprint.png", (clip_x, clip_y), self._size

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