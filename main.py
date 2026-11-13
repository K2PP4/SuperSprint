from src.lib.g2d import init_canvas, main_loop, current_keys, close_canvas
from src.lib.actor import Arena, Actor
from src.enums import Arena_size, Car_colors
from src.classes import UsrCar
from src.funcs import draw_actor
from src.lib.g2d import clear_canvas

arena = Arena(Arena_size.dims.value)

def main():
    init_canvas(Arena_size.dims.value)
    p1_car = UsrCar((250,250),Car_colors.red, "tester")
    arena.spawn(p1_car)
    main_loop(tick)

def tick():
    clear_canvas()
    cur_keys = current_keys()
    arena.tick(cur_keys)
    for a in arena.actors():
        draw_actor(a)
    if "Escape" in cur_keys:
        close_canvas()

if __name__ == "__main__":
    print("Started main (main.py)")
    main()