from src.lib.g2d import init_canvas, main_loop, current_keys, close_canvas, clear_canvas, key_pressed
from src.lib.actor import Arena, Actor
from src.enums import Arena_size, Car_colors
from src.classes import UsrCar
from src.funcs import draw_actor, init_arena, draw_debug_info

arena = Arena(Arena_size.dims.value)
p1_car = UsrCar((227, 143), Car_colors.red, "tester")
debug_mode = False

def main():
    init_canvas(Arena_size.dims.value)
    arena.spawn(p1_car)
    main_loop(tick)

def tick():
    global debug_mode
    clear_canvas()
    init_arena(1)

    cur_keys = current_keys()
    if key_pressed("w") or key_pressed("W"):
        debug_mode = not debug_mode

    arena.tick(cur_keys)
    for a in arena.actors():
        draw_actor(a)

    if debug_mode:
        draw_debug_info(p1_car, lvl=1)

    if "Escape" in cur_keys:
        close_canvas()

if __name__ == "__main__":
    print("Started main (main.py)")
    main()
