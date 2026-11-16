from src.lib.g2d import init_canvas, main_loop, current_keys, close_canvas, clear_canvas, key_pressed
from src.lib.actor import Arena, Actor
from src.enums import Arena_size, Car_colors
from src.classes import UsrCar, CpuCar
from src.funcs import draw_actor, init_arena, draw_debug_info, load_waypoints

arena = Arena(Arena_size.dims.value)
debug_mode = False

# Carica i waypoint definiti con '@' nella mappa del livello 1
# Partenza dal rettilineo alto, direzione verso destra (antiorario)
waypoints = load_waypoints(1, start_pos=(168, 92), start_heading=(1.0, 0.0))

# ── Griglia di partenza sul rettilineo alto (Finish Line) ──
# Le auto partono affiancate verticalmente, rivolte a destra (0°) per il senso antiorario
# Posizione: appena prima della FL (x=160), y staggered a righe 10-13
START_X     = 160
START_Y_GAP = 8                     # 8px tra ogni auto (compatto come nell'arcade)
START_ANGLE = 180                   # Facing right (counter-clockwise on top straight)

cpu_yellow = CpuCar((START_X, 80),               Car_colors.yellow, "CPU 1", waypoints=waypoints, max_speed=9)
cpu_blue   = CpuCar((START_X, 80 + START_Y_GAP), Car_colors.blue,   "CPU 2", waypoints=waypoints, max_speed=4)
p1_car     = UsrCar((START_X, 80 + START_Y_GAP * 2), Car_colors.red, "Player")
p1_car._angle     = START_ANGLE
p1_car._max_speed = 4.5             # Velocità massima ridotta per il giocatore
cpu_white  = CpuCar((START_X, 80 + START_Y_GAP * 3), Car_colors.white, "CPU 3", waypoints=waypoints, max_speed=3)

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
