from src.lib.g2d import init_canvas, main_loop, current_keys, close_canvas, clear_canvas, key_pressed
from src.lib.actor import Arena, Actor
from src.enums import Arena_size, Car_colors
from src.classes import UsrCar, CpuCar
from src.funcs import draw_actor, init_arena, draw_debug_info, load_waypoints

arena = Arena(Arena_size.dims.value)
debug_mode = False

# Carica i waypoint definiti con '@' nella mappa del livello 1
waypoints = load_waypoints(1)

# Allinea le 4 auto sulla linea di partenza, una affianco all'altra, rivolte a sinistra (180°)
cpu_yellow = CpuCar((175, 338), Car_colors.yellow, "CPU 1", waypoints=waypoints, max_speed=5.3)
cpu_blue   = CpuCar((175, 354), Car_colors.blue,   "CPU 2", waypoints=waypoints, max_speed=5.0)
p1_car     = UsrCar((175, 370), Car_colors.red,    "Player")
p1_car._angle = 180.0
cpu_white  = CpuCar((175, 386), Car_colors.white,  "CPU 3", waypoints=waypoints, max_speed=4.7)

def main():
    init_canvas(Arena_size.dims.value)
    arena.spawn(p1_car)
    arena.spawn(cpu_yellow)
    arena.spawn(cpu_blue)
    arena.spawn(cpu_white)
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
