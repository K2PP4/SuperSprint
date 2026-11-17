from math import dist
from src.lib import g2d
from src.classes import Car

CHECKPOINT_RADIUS = 40      # px: how close a car must pass to a checkpoint to hit it

def ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 3 -> '3rd', 4 -> '4th', ..."""
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

class Race:
    """
    Keeps track of laps, finishing order and times for a set of cars.

    A lap is counted when a car crosses the finish line (FL) while driving in the
    race direction (right to left, counter-clockwise) AFTER hitting every checkpoint
    in order. So the crossing at the start of the race, driving backwards or
    wiggling back and forth across the line never counts.
    """
    def __init__(self, cars: list[Car], checkpoints: list[tuple[float, float]],
                 finish_zone: tuple[float, float, float], total_laps: int = 3,
                 fps: int = 30, log=print):
        """
        cars:         all cars in the race
        checkpoints:  ordered points of the track (the CPU waypoints work well)
        finish_zone:  (x, y_top, y_bottom) of the finish line, see funcs.load_finish_zone
        total_laps:   laps needed to finish
        fps:          frames per second, to convert frames to seconds
        log:          function used to report events (lap completed, finish...)
        """
        self.cars = list(cars)
        self.checkpoints = checkpoints
        self.fl_x, self.fl_top, self.fl_bottom = finish_zone
        self.total_laps = total_laps
        self.fps = fps
        self._log = log
        self.frames = 0
        self._prev_x = {c: c.center[0] for c in self.cars}      # x of the previous frame
        self._lap_start = {c: 0 for c in self.cars}             # frame at which the current lap began
        self.lap_times: dict[Car, list[float]] = {c: [] for c in self.cars}
        self.finish_times: dict[Car, float] = {}
        self._next_rank = 1
        self._summary_printed = False

    @property
    def seconds(self) -> float:
        return self.frames / self.fps

    @property
    def is_over(self) -> bool:
        return all(c.is_finished for c in self.cars)

    def update(self):
        """
        Call once per frame, after the arena tick: updates checkpoints and laps.
        """
        self.frames += 1
        for car in self.cars:
            if car.is_finished:
                continue
            cx, cy = car.center

            # 1. Checkpoints must be hit in order
            while (car.target_checkpoint_index < len(self.checkpoints) and
                   dist((cx, cy), self.checkpoints[car.target_checkpoint_index]) < CHECKPOINT_RADIUS):
                car.advance_checkpoint()

            # 2. Finish line: crossed leftwards (previous x >= line > current x) within the road
            prev_x, self._prev_x[car] = self._prev_x[car], cx
            crossed = prev_x >= self.fl_x > cx and self.fl_top <= cy < self.fl_bottom
            if crossed and car.target_checkpoint_index >= len(self.checkpoints):
                self._complete_lap(car)

        if self.is_over and not self._summary_printed:
            self._summary_printed = True
            self._print_summary()

    def _complete_lap(self, car: Car):
        car.complete_lap()
        lap_time = (self.frames - self._lap_start[car]) / self.fps
        self._lap_start[car] = self.frames
        self.lap_times[car].append(lap_time)
        self._log(f"{car.name}: lap {car.laps}/{self.total_laps} in {lap_time:.1f}s")
        if car.laps >= self.total_laps:
            car.finish(self._next_rank)
            self.finish_times[car] = self.seconds
            self._log(f"{car.name} FINISHED {ordinal(self._next_rank)} ({self.seconds:.1f}s)")
            self._next_rank += 1

    def standings(self) -> list[Car]:
        """
        Cars sorted by race position (1st first). Finished cars come first, in
        finishing order; the others by laps, then checkpoints, then how close
        they are to the next checkpoint.
        """
        def progress(car: Car):
            idx = car.target_checkpoint_index
            nxt = self.checkpoints[min(idx, len(self.checkpoints) - 1)]
            return (-car.laps, -idx, dist(car.center, nxt))

        done = sorted((c for c in self.cars if c.is_finished), key=lambda c: c.finish_rank)
        running = sorted((c for c in self.cars if not c.is_finished), key=progress)
        return done + running

    def position(self, car: Car) -> int:
        """Current race position of `car` (1 = leader)."""
        return self.standings().index(car) + 1

    def _print_summary(self):
        self._log("── Final results ──")
        for i, car in enumerate(self.standings(), start=1):
            best = min(self.lap_times[car]) if self.lap_times[car] else 0.0
            self._log(f"{ordinal(i)}  {car.name:<8} {self.finish_times[car]:6.1f}s  (best lap {best:.1f}s)")

    def draw_hud(self, player: Car):
        """
        Draws lap / position / wrenches / time in the black bar at the top of the
        screen (y < 64), and a finish banner once the player has finished.
        """
        lap = min(player.laps + 1, self.total_laps)
        last = self.lap_times[player][-1] if self.lap_times[player] else None
        g2d.set_color((255, 255, 255))
        g2d.draw_text(f"LAP {lap}/{self.total_laps}", (96, 18), 18)
        g2d.draw_text(f"POS {self.position(player)}/{len(self.cars)}", (256, 18), 18)
        g2d.draw_text(f"WRENCH {player.wrenches}", (416, 18), 18)
        g2d.set_color((190, 190, 190))
        g2d.draw_text(f"LAST {last:.1f}s" if last is not None else "LAST --", (96, 44), 14)
        g2d.draw_text(f"TIME {self.seconds:.1f}s", (256, 44), 14)
        g2d.draw_text(f"BEST {min(self.lap_times[player]):.1f}s" if self.lap_times[player] else "BEST --",
                      (416, 44), 14)

        if player.is_finished:
            g2d.set_color((255, 220, 0))
            g2d.draw_text(f"FINISH!  {ordinal(player.finish_rank)} place", (256, 240), 30)
