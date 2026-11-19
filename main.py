from src.lib.g2d import init_canvas, main_loop, current_keys, close_canvas, clear_canvas, key_pressed
from src.lib.actor import Arena, Actor
from src.enums import Arena_size, Car_colors
from src.classes import UsrCar, CpuCar, Wrench, OilPuddle
from src.funcs import draw_actor, init_arena, draw_debug_info, load_waypoints, load_items, load_gates
from src.race import Race

arena = Arena(Arena_size.dims.value)

# ── Starting grid ──
# The cars drive COUNTER-CLOCKWISE: along the top straight that means heading LEFT
# (angle 180°). The grid is placed just RIGHT of the finish line (FL, around x=236),
# so every car starts behind the line and crosses it while driving left.
START_X     = 264                                       # left edge of the grid, right of the FL
START_Y     = 80                                        # y of the first car on the top straight
START_Y_GAP = 8                                         # px between cars (compact, like the arcade)
START_ANGLE = 180                                       # 180° = facing left, same angle for ALL cars
TOTAL_LAPS = 3

# Waypoints ('@' in the level map), ordered counter-clockwise starting from the grid
waypoints = load_waypoints(1, start_pos=(START_X, START_Y + 12), start_heading=(-1.0, 0.0))

def grid_pos(slot: int) -> tuple[int, int]:
    """Position of the car in the given grid slot (0 = topmost)."""
    return (START_X, START_Y + START_Y_GAP * slot)

# Slot order top to bottom: CPU 1, CPU 2, Player, CPU 3
cpu_yellow = CpuCar(grid_pos(0), Car_colors.yellow, "CPU 1", waypoints=waypoints, max_speed=5, angle=START_ANGLE)
cpu_blue   = CpuCar(grid_pos(1), Car_colors.blue,   "CPU 2", waypoints=waypoints, max_speed=4, angle=START_ANGLE)
p1_car     = UsrCar(grid_pos(2), Car_colors.red,    "Player", angle=START_ANGLE)
p1_car.max_speed = 5
cpu_white  = CpuCar(grid_pos(3), Car_colors.white,  "CPU 3", waypoints=waypoints, max_speed=3, angle=START_ANGLE)

# ── Race: laps, positions, finish order ──
# Lines drawn across the whole road in the map: 'F' = finish line, 'S' = splits.
# CPU cars count laps with the waypoints (checkpoints); the player counts them by crossing the splits and then the finish line.

finish_line, splits = load_gates(1, waypoints)
race = Race([cpu_yellow, cpu_blue, p1_car, cpu_white],  # grid order: breaks ties at the start
            checkpoints=waypoints,
            finish=finish_line, splits=splits,
            total_laps=TOTAL_LAPS, log=log)

def spawn_items(lvl: int = 1):
    """Create wrenches ('w') and oil puddles ('p') from the level map."""
    for c in load_items(lvl, "w"):
        arena.spawn(Wrench(c))
    for c in load_items(lvl, "p"):
        arena.spawn(OilPuddle(c))

def main():
    init_canvas(Arena_size.dims.value, 2)
    spawn_items(1)                                      # items first: actors are drawn in spawn order, so cars end up on top
    arena.spawn(p1_car)
    arena.spawn(cpu_yellow)
    arena.spawn(cpu_blue)
    arena.spawn(cpu_white)
    main_loop(tick)

def tick():
    # Redraw the background (track) every frame
    clear_canvas()
    init_arena(1)

    cur_keys = current_keys()

    # Advance the game one frame and draw every actor
    arena.tick(cur_keys)
    race.update()                                       # checkpoints, lap counting, finish order
    for a in arena.actors():
        draw_actor(a)
    race.draw_hud(p1_car)                               # lap / position / time in the top bar

    if "Escape" in cur_keys:
        close_canvas()

if __name__ == "__main__":
    print("Started main (main.py)")
    main()
