from src.lib.g2d import (
    init_canvas,
    main_loop,
    current_keys,
    close_canvas,
    clear_canvas,
    key_pressed,
)
from src.lib.actor import Arena
from src.enums import Arena_size, Car_colors
from src.classes import UsrCar, CpuCar, Wrench, OilPuddle
from src.funcs import (
    draw_actor,
    init_arena,
    draw_debug_info,
    load_waypoints,
    load_items,
    load_gates,
)
from src.race import Race


class SuperSprintGUI:
    DEBUG_WINDOW = 30

    def __init__(self, game: "SuperSprintGme"):
        self.game = game
        self.debug_mode = False
        self.debug_frames = 0
        self.debug_keys: set[str] = set()

    def run(self):
        init_canvas(Arena_size.dims.value)
        self.game.spawn_items()
        self.game.arena.spawn(self.game.player)
        self.game.arena.spawn(self.game.cpu_yellow)
        self.game.arena.spawn(self.game.cpu_blue)
        self.game.arena.spawn(self.game.cpu_white)
        main_loop(self.tick)

    def tick(self):
        clear_canvas()
        init_arena(self.game.level)

        cur_keys = current_keys()
        if key_pressed("w") or key_pressed("W"):
            self.set_debug(not self.debug_mode)

        self.game.arena.tick(cur_keys)
        self.game.race.update()
        for actor in self.game.arena.actors():
            draw_actor(actor)
        self.game.race.draw_hud(self.game.player)

        if self.debug_mode:
            draw_debug_info(
                self.game.player,
                lvl=self.game.level,
                gates=(self.game.finish_line, self.game.splits),
            )
            self.update_debug_console(cur_keys)

        if "Escape" in cur_keys:
            close_canvas()

    def set_debug(self, enabled: bool):
        self.debug_mode = enabled
        self.debug_frames = 0
        self.debug_keys.clear()
        if enabled:
            print("Debug mode ON  (press W to turn it off)")
        else:
            print("\nDebug mode OFF")

    def update_debug_console(self, keys: list[str]):
        self.debug_keys.update(keys)
        self.debug_frames += 1
        if self.debug_frames % self.DEBUG_WINDOW == 0:
            step = (self.debug_frames // self.DEBUG_WINDOW - 1) % 3 + 1
            dots = ("." * step).ljust(3)
            pressed = ", ".join(sorted(self.debug_keys)) or "none"
            line = f"Debug mode running{dots} | keys (last {self.DEBUG_WINDOW}f): {pressed}"
            print("\r" + line.ljust(78), end="", flush=True)
            self.debug_keys.clear()


class SuperSprintGme:
    START_X = 264
    START_Y = 80
    START_Y_GAP = 8
    START_ANGLE = 180
    TOTAL_LAPS = 3

    def __init__(self, level: int = 1):
        self.level = level
        self.arena = Arena(Arena_size.dims.value)
        self.waypoints = load_waypoints(
            self.level,
            start_pos=(self.START_X, self.START_Y + 12),
            start_heading=(-1.0, 0.0),
        )

        self.cpu_yellow = CpuCar(
            self.grid_pos(0),
            Car_colors.yellow,
            "CPU 1",
            waypoints=self.waypoints,
            max_speed=5,
            angle=self.START_ANGLE,
        )
        self.cpu_blue = CpuCar(
            self.grid_pos(1),
            Car_colors.blue,
            "CPU 2",
            waypoints=self.waypoints,
            max_speed=4,
            angle=self.START_ANGLE,
        )
        self.player = UsrCar(
            self.grid_pos(2),
            Car_colors.red,
            "Player",
            angle=self.START_ANGLE,
        )
        self.player.max_speed = 5
        self.cpu_white = CpuCar(
            self.grid_pos(3),
            Car_colors.white,
            "CPU 3",
            waypoints=self.waypoints,
            max_speed=3,
            angle=self.START_ANGLE,
        )

        self.finish_line, self.splits = load_gates(self.level, self.waypoints)
        self.race = Race(
            [self.cpu_yellow, self.cpu_blue, self.player, self.cpu_white],
            checkpoints=self.waypoints,
            finish=self.finish_line,
            splits=self.splits,
            total_laps=self.TOTAL_LAPS,
            log=self.log,
        )
        self.gui = SuperSprintGUI(self)

    def grid_pos(self, slot: int) -> tuple[int, int]:
        return (self.START_X, self.START_Y + self.START_Y_GAP * slot)

    def log(self, message: str):
        print("\r" + message.ljust(78))

    def spawn_items(self):
        for center in load_items(self.level, "w"):
            self.arena.spawn(Wrench(center))
        for center in load_items(self.level, "p"):
            self.arena.spawn(OilPuddle(center))

    def run(self):
        self.gui.run()


if __name__ == "__main__":
    print("Started main (main.py)")
    SuperSprintGme().run()
