from src.lib.g2d import init_canvas, main_loop, current_keys, close_canvas, clear_canvas, key_pressed
from src.lib.actor import Arena, Actor
from src.enums import Arena_size, Car_colors
from src.classes import UsrCar, CpuCar, Wrench, OilPuddle
from src.funcs import draw_actor, init_arena, draw_debug_info, load_waypoints, load_items, load_finish_zone
from src.race import Race

arena = Arena(Arena_size.dims.value)

# ── Debug mode state ──
DEBUG_WINDOW = 30                                       # frames between console updates
debug_mode = False
debug_frames = 0                                        # frames elapsed since debug mode was enabled
debug_keys: set[str] = set()                            # keys seen during the current 30-frame window

# ── Starting grid ──
# The cars drive COUNTER-CLOCKWISE: along the top straight that means heading LEFT
# (angle 180°). The grid is placed just RIGHT of the finish line (FL, around x=236),
# so every car starts behind the line and crosses it while driving left.
START_X     = 264                                       # left edge of the grid, right of the FL
START_Y     = 80                                        # y of the first car on the top straight
START_Y_GAP = 8                                         # px between cars (compact, like the arcade)
START_ANGLE = 180                                       # 180° = facing left, same angle for ALL cars

# Waypoints ('@' in the level map), ordered counter-clockwise starting from the grid
waypoints = load_waypoints(1, start_pos=(START_X, START_Y + 12), start_heading=(-1.0, 0.0))

def grid_pos(slot: int) -> tuple[int, int]:
    """Position of the car in the given grid slot (0 = topmost)."""
    return (START_X, START_Y + START_Y_GAP * slot)

# Slot order top to bottom: CPU 1, CPU 2, Player, CPU 3
cpu_yellow = CpuCar(grid_pos(0), Car_colors.yellow, "CPU 1", waypoints=waypoints, max_speed=9, angle=START_ANGLE)
cpu_blue   = CpuCar(grid_pos(1), Car_colors.blue,   "CPU 2", waypoints=waypoints, max_speed=4, angle=START_ANGLE)
p1_car     = UsrCar(grid_pos(2), Car_colors.red,    "Player", angle=START_ANGLE)
p1_car._max_speed = 4.5             # reduced top speed for the player
cpu_white  = CpuCar(grid_pos(3), Car_colors.white,  "CPU 3", waypoints=waypoints, max_speed=3, angle=START_ANGLE)

def log(message: str):
    """
    Print an event on its own console line. The leading '\\r' and the padding make it
    safe even while the in-place debug status line is on screen.
    """
    print("\r" + message.ljust(78))

# ── Race: laps, positions, finish order ──
TOTAL_LAPS = 3
race = Race([p1_car, cpu_yellow, cpu_blue, cpu_white],
            checkpoints=waypoints,                      # the CPU waypoints double as checkpoints
            finish_zone=load_finish_zone(1),            # FL position from the 'F' tile in the map
            total_laps=TOTAL_LAPS, log=log)

def spawn_items(lvl: int = 1):
    """Create wrenches ('w') and oil puddles ('p') from the level map."""
    for c in load_items(lvl, "w"):
        arena.spawn(Wrench(c))
    for c in load_items(lvl, "p"):
        arena.spawn(OilPuddle(c))

def set_debug(enabled: bool):
    """Turn debug mode on/off and reset the console counters."""
    global debug_mode, debug_frames
    debug_mode = enabled
    debug_frames = 0
    debug_keys.clear()
    if enabled:
        print("Debug mode ON  (press W to turn it off)")
    else:
        print("\nDebug mode OFF")

def update_debug_console(keys: list[str]):
    """
    Called once per frame while debug mode is on. Collects the keys pressed and,
    every DEBUG_WINDOW frames, redraws a single console line in place, CLI-spinner style:
        Debug mode running.   | keys (last 30f): ArrowUp, ArrowLeft
        Debug mode running..  | ...
        Debug mode running... | ...
    """
    global debug_frames
    debug_keys.update(keys)
    debug_frames += 1
    if debug_frames % DEBUG_WINDOW == 0:
        step = (debug_frames // DEBUG_WINDOW - 1) % 3 + 1       # cycles 1, 2, 3 dots
        dots = ("." * step).ljust(3)
        pressed = ", ".join(sorted(debug_keys)) or "none"
        line = f"Debug mode running{dots} | keys (last {DEBUG_WINDOW}f): {pressed}"
        # '\r' returns to the start of the line; padding erases a longer previous line
        print("\r" + line.ljust(78), end="", flush=True)
        debug_keys.clear()

def main():
    init_canvas(Arena_size.dims.value)
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

    # W toggles debug mode (walls/waypoints overlay + console status line)
    if key_pressed("w") or key_pressed("W"):
        set_debug(not debug_mode)

    # Advance the game one frame and draw every actor
    arena.tick(cur_keys)
    race.update()                                       # checkpoints, lap counting, finish order
    for a in arena.actors():
        draw_actor(a)
    race.draw_hud(p1_car)                               # lap / position / time in the top bar

    if debug_mode:
        draw_debug_info(p1_car, lvl=1)
        update_debug_console(cur_keys)

    if "Escape" in cur_keys:
        close_canvas()

if __name__ == "__main__":
    print("Started main (main.py)")
    main()
