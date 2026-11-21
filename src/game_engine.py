from math import ceil
import os
import pygame as pg

from src.lib.g2d import (
    init_canvas,
    main_loop,
    current_keys,
    close_canvas,
    clear_canvas,
    key_pressed,
    alert,
    set_color,
    draw_text,
)
from src.lib.actor import Arena
from src.enums import Arena_size, Car_colors
from src.classes import Car, UsrCar, CpuCar, Wrench, OilPuddle
from src.funcs import (
    draw_actor,
    init_arena,
    load_waypoints,
    load_items,
    load_gates,
)
from src.race import Race
from src.lib import g2d

class GameEngine:
    def __init__(self):
        self._game = SuperSprintGame()
        self._gui = SuperSprintGui(game=self._game)

    def startup(self):
        init_canvas(Arena_size.dims.value)
        main_loop(self._gui.tick, SuperSprintGame.FPS)


class SuperSprintGame:
    """
    Builds the characters from the level configuration file
    (maps/lvl-N.txt), encapsulates cars and arena, runs the start countdown
    and checks how the race ends.
    """
    FPS = 30
    COUNTDOWN_SECONDS = 5
    START_X = 264
    START_Y = 80
    START_Y_GAP = 20
    START_ANGLE = 180
    TOTAL_LAPS = 3
    PLAYER_NAME = "Player"

    KEY_ALIASES = {
        "w": "ArrowUp",
        "a": "ArrowLeft",
        "s": "ArrowDown",
        "d": "ArrowRight",
    }

    def __init__(self, level: int = 1):
        self.level = level
        self.arena = Arena(Arena_size.dims.value)
        self.countdown_frames = self.COUNTDOWN_SECONDS * self.FPS
        self.yellow_flag_frames = 0
        self.finish_delay_frames = 0
        self.finish_delay_started = False
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
            self.PLAYER_NAME,
            angle=self.START_ANGLE,
        )
        self.player.max_speed(5)
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
            fps=self.FPS,
            log=self.log,
        )
        self.spawn_actors()

    def grid_pos(self, slot: int) -> tuple[int, int]:
        return (self.START_X, self.START_Y + self.START_Y_GAP * slot)

    def log(self, message: str):
        print("\r" + message)

    def spawn_actors(self):
        """Puts items (from the map file) and cars into the arena."""
        for center in load_items(self.level, "w"):
            self.arena.spawn(Wrench(center))
        for center in load_items(self.level, "p"):
            self.arena.spawn(OilPuddle(center))
        for car in self.race.cars:
            self.arena.spawn(car)

    @classmethod
    def map_keys(cls, keys: list[str]) -> list[str]:
        """Maps the arrow-key equivalent of every WASD key pressed."""
        mapped = list(keys)
        for key in keys:
            alias = cls.KEY_ALIASES.get(key.lower())
            if alias and alias not in mapped:
                mapped.append(alias)
        return mapped

    @property
    def is_counting_down(self) -> bool:
        return self.countdown_frames > 0

    @property
    def countdown_seconds(self) -> int:
        return ceil(self.countdown_frames / self.FPS)

    def go_visible(self) -> bool:
        return not self.is_counting_down and self.race.frames < self.FPS

    def check_car_collisions(self):
        """Checks mutual collisions between all cars in the race."""
        cars = self.race.cars
        for i in range(len(cars)):
            for j in range(i + 1, len(cars)):
                if cars[i].collides_with_other(cars[j]):
                    self.yellow_flag_frames = 30

    def tick(self, keys: list[str]):
        """
        Advances the game by one frame. During the countdown the cars stay on the
        grid and the race clock does not run.
        """
        if self.is_counting_down:
            self.countdown_frames -= 1
            return
        self.arena.tick(self.map_keys(keys))
        self.check_car_collisions()
        if self.yellow_flag_frames > 0:
            self.yellow_flag_frames -= 1
        self.race.update()
        if any(car.is_finished for car in self.race.cars):
            if not self.finish_delay_started:
                self.finish_delay_frames = 5 * self.FPS
                self.finish_delay_started = True
            elif self.finish_delay_frames > 0:
                self.finish_delay_frames -= 1

    def game_over(self) -> bool:
        return (self.finish_delay_started
                and self.finish_delay_frames == 0)

    def game_won(self) -> bool:
        return self.player.is_finished and self.player.finish_rank == 1


class SuperSprintGui:
    """
    Representation of the game: drawing (images and g2d functions),
    keyboard input and the tick method.
    """
    FLAG_SOURCE_SIZE = (16, 16)
    FLAG_DRAW_SIZE = (32, 32)
    FLAG_POS = (472, 16)
    YELLOW_FLAG_ROW = 128
    CHECKER_FLAG_ROW = 160
    FLAG_FIRST_FRAME_X = 128
    FLAG_FRAME_COUNT = 8
    FLAG_FRAME_MS = 4

    def __init__(self, game: SuperSprintGame):
        self.game = game
        self.flag_sheet = None
        self.flag_sprite_sheet = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "img",
            "super-sprint.png",
        )

    def draw_countdown(self):
        if self.game.is_counting_down:
            set_color((255, 220, 0))
            draw_text(str(self.game.countdown_seconds), (256, 240), 80)
        elif self.game.go_visible():
            set_color((0, 255, 0))
            draw_text("GO!", (256, 240), 80)

    def draw_scaled_sprite_flag(self, pos: tuple[int, int], clip_pos: tuple[int, int]):
        if self.flag_sheet is None:
            self.flag_sheet = pg.image.load(self.flag_sprite_sheet).convert_alpha()
        tile = self.flag_sheet.subsurface(
            pg.Rect(clip_pos[0], clip_pos[1],
                    self.FLAG_SOURCE_SIZE[0], self.FLAG_SOURCE_SIZE[1])
        )
        scaled = pg.transform.smoothscale(tile, self.FLAG_DRAW_SIZE)
        g2d.drawing_surface().blit(scaled, pos)

    def draw_race_flags(self):
        """Draws the animated yellow flag for incidents and the checkered flag at the finish."""
        frame = (self.game.race.frames // self.FLAG_FRAME_MS) % self.FLAG_FRAME_COUNT
        clip_x = self.FLAG_FIRST_FRAME_X + frame * self.FLAG_SOURCE_SIZE[0]

        if any(car.is_finished for car in self.game.race.cars):
            self.draw_scaled_sprite_flag(
                self.FLAG_POS,
                (clip_x, self.CHECKER_FLAG_ROW),
            )
        elif (any(car.is_spinning for car in self.game.race.cars)
                or self.game.yellow_flag_frames > 0):
            self.draw_scaled_sprite_flag(
                self.FLAG_POS,
                (clip_x, self.YELLOW_FLAG_ROW),
            )

    def tick(self):
        clear_canvas()
        init_arena(self.game.level)

        cur_keys = current_keys()

        self.game.tick(cur_keys)
        for actor in self.game.arena.actors():
            draw_actor(actor)
        self.game.race.draw_hud(self.game.player)
        self.draw_race_flags()
        self.draw_countdown()

        if self.game.game_over():
            if self.game.game_won():
                alert("You win!")
            else:
                alert("Race finished, better luck next time!")
            close_canvas()

        if "Escape" in cur_keys:
            close_canvas()
