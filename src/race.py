from math import dist
from src.lib import g2d
from src.classes import Car
from src.funcs import Gate

CHECKPOINT_RADIUS = 40                                  # px: how close a CPU car must pass to a checkpoint to hit it

def ordinal(n: int) -> str:
    """1 -> '1st', 2 -> '2nd', 3 -> '3rd', 4 -> '4th', ..."""
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

class Race:
    """
    Keeps track of laps, positions, finishing order and times for a set of cars.

    A lap is a sequence of "gates" ending with the finish line (FL):
      - CPU cars (tracking = "checkpoints"): hit every checkpoint (waypoint), in order,
        then cross the FL in the race direction.
      - Player cars (tracking = "splits"): cross every split line 'S' of the map, in order,
        then the FL. The lines span the whole road, so they cannot be missed by driving
        a slightly different line.
    In both modes the crossing at the start of the race does not count, and crossing a
    line backwards undoes it, so driving back and forth over a line never gains anything.
    """
    def __init__(self, cars: list[Car], checkpoints: list[tuple[float, float]],
                 finish: Gate, splits: list[Gate], total_laps: int = 3,
                 fps: int = 30, log=print):
        """
        cars:         all cars in the race, in grid order (used to break ties in the positions)
        checkpoints:  ordered waypoints of the track; also the racing line used for positions
        finish:       finish line gate (funcs.load_gates)
        splits:       split gates in lap order (funcs.load_gates)
        total_laps:   laps needed to finish
        fps:          frames per second, to convert frames to seconds
        log:          function used to report events (split, lap completed, finish...)
        """
        self.cars = list(cars)
        self.checkpoints = checkpoints
        self.finish = finish
        self.splits = splits
        self.total_laps = total_laps
        self.fps = fps
        self._log = log
        self.frames = 0
        self._gates = {c: 0 for c in self.cars}         # gates passed in sequence (can go back)
        self._best = {c: 0 for c in self.cars}          # most gates ever passed: events fire once
        self._prev_pos = {c: c.center for c in self.cars}  # position at the previous frame
        self._lap_start = {c: 0 for c in self.cars}     # frame at which the current lap began
        self._prev_u = {c: self._track_u(c.center) for c in self.cars}
        self._progress = {c: 0.0 for c in self.cars}    # laps driven along the track (for positions)
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

    def _mode(self, car: Car) -> str:
        """Tracking mode of `car`; a player car falls back to checkpoints if the map has no splits."""
        return "splits" if car.tracking == "splits" and self.splits else "checkpoints"

    def _lap_length(self, car: Car) -> int:
        """Number of gates in one lap for `car`: its checkpoints/splits plus the finish line."""
        return (len(self.splits) if self._mode(car) == "splits" else len(self.checkpoints)) + 1

    def _track_u(self, pt: tuple[float, float]) -> float:
        """Position along the racing line, from 0 (finish line) to 1 (back at the finish line)."""
        n = len(self.checkpoints)
        best_d, best_s = float("inf"), 0.0
        for k in range(n):
            a, b = self.checkpoints[k], self.checkpoints[(k + 1) % n]
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dy) / ((dx * dx + dy * dy) or 1)
            t = max(0.0, min(1.0, t))
            d = dist(pt, (a[0] + t * dx, a[1] + t * dy))
            if d < best_d:
                best_d, best_s = d, k + t
        return ((best_s - self.finish.order) % n) / n

    def _advance(self, car: Car, prev: tuple, cur: tuple, g: int) -> int:
        """Returns the new number of gates passed by `car` after moving from `prev` to `cur`."""
        if self._mode(car) == "splits":
            gates = self.splits + [self.finish]
            if gates[g % len(gates)].crossing(prev, cur) == 1:  # next gate, forward
                return g + 1
            if g > 0 and gates[(g - 1) % len(gates)].crossing(prev, cur) == -1:  # last gate, backwards
                return g - 1
            return g
        n = len(self.checkpoints)
        while g % (n + 1) < n and dist(cur, self.checkpoints[g % (n + 1)]) < CHECKPOINT_RADIUS:
            g += 1                                      # next checkpoint hit
        if g % (n + 1) == n and self.finish.crossing(prev, cur) == 1:  # all hit: FL closes the lap
            g += 1
        return g

    def update(self):
        """
        Call once per frame, after the arena tick: updates splits/checkpoints, laps and positions.
        """
        self.frames += 1
        for car in self.cars:
            if car.is_finished:
                continue
            prev, cur = self._prev_pos[car], car.center
            self._prev_pos[car] = cur

            # Positions: add the (wrapped) distance driven along the track since the last frame
            u = self._track_u(cur)
            self._progress[car] += (u - self._prev_u[car] + 0.5) % 1.0 - 0.5
            self._prev_u[car] = u

            # Gates: splits/checkpoints and finish line
            g = self._advance(car, prev, cur, self._gates[car])
            if g == self._gates[car]:
                continue
            self._gates[car] = g
            length = self._lap_length(car)
            car.set_race_progress(g // length, g % length, g)
            if g > self._best[car]:                     # only NEW progress scores
                self._best[car] = g
                if g % length == 0:
                    self._complete_lap(car)
                elif self._mode(car) == "splits":
                    lap_time = (self.frames - self._lap_start[car]) / self.fps
                    self._log(f"{car.name}: split {g % length}/{length - 1} at {lap_time:.1f}s")

        if self.is_over and not self._summary_printed:
            self._summary_printed = True
            self._print_summary()

    def _complete_lap(self, car: Car):
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
        Cars sorted by race position (1st first). Finished cars come first, in finishing
        order; the others by distance driven along the track. Ties keep the grid order.
        """
        done = sorted((c for c in self.cars if c.is_finished), key=lambda c: c.finish_rank)
        running = sorted((c for c in self.cars if not c.is_finished), key=lambda c: -self._progress[c])
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
        screen (y < 64).
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
