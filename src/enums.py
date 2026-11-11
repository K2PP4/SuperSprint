from enum import Enum

class Car_colors(Enum):
    yellow  = 0,
    blue    = 1,
    red     = 2,
    white   = 3

class Car_size(Enum):
    width   = 16,
    height  = 16,
    dims    = (16,16)

class Arena_size(Enum):
    width = 512,
    height = 512,
    dims = (512, 512)