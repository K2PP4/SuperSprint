import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

try:
    import tkinter
    _tk = tkinter.Tk()
    _tk.destroy()
except Exception:
    from unittest.mock import MagicMock
    tkinter.Tk = MagicMock()

import unittest

from src.lib import g2d
from src.lib.actor import Arena
from src.enums import Arena_size, Car_colors
from src.classes import UsrCar, CpuCar, Wrench, OilPuddle
from src.funcs import (
    get_cached_walls,
    is_in_bounds,
    load_items,
    load_waypoints,
    load_gates,
)
from src.race import ordinal
from src.game_engine import SuperSprintGame, SuperSprintGui


def quiet_game() -> SuperSprintGame:
    """A new game whose race log does not clutter the test output."""
    game = SuperSprintGame()
    game.race._log = lambda *_: None
    return game


def skip_countdown(game: SuperSprintGame):
    game.countdown_frames = 0


class TestMap(unittest.TestCase):
    def setUp(self):
        self.walls = get_cached_walls(1)

    def test_arena_size(self):
        self.assertEqual(Arena_size.dims.value, (512, 480))
        self.assertEqual(Arena(Arena_size.dims.value).size(), (512, 480))

    def test_map_is_64x60_with_closed_border(self):
        self.assertEqual(len(self.walls), 60)
        for row in self.walls:
            self.assertEqual(len(row), 64)
        self.assertTrue(all(ch == "#" for ch in self.walls[0]))
        self.assertTrue(all(ch == "#" for ch in self.walls[-1]))
        self.assertTrue(all(row[0] == "#" and row[-1] == "#" for row in self.walls))

    def test_images_exist(self):
        car = UsrCar((250, 250), Car_colors.red)
        img_path, _, clip_size = car.get_sprite_cutout()
        self.assertTrue(os.path.exists(img_path))
        self.assertEqual(clip_size, (16, 16))
        bg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "img", "super-sprint-bg.png")
        self.assertTrue(os.path.exists(bg))

    def test_waypoints_are_all_on_the_road(self):
        wps = load_waypoints(1)
        self.assertEqual(len(wps), len(load_items(1, "@")))
        self.assertEqual(len(set(wps)), len(wps))
        arena = Arena(Arena_size.dims.value)
        car = UsrCar((0, 0), Car_colors.yellow)
        for wp in wps:
            self.assertTrue(is_in_bounds(car, arena, 1, pos=(wp[0] - 8, wp[1] - 8)), f"waypoint {wp}")

    def test_in_bounds(self):
        arena = Arena(Arena_size.dims.value)
        car = UsrCar((250, 250), Car_colors.red)
        self.assertTrue(is_in_bounds(car, arena, 1, pos=(250, 250)))
        self.assertFalse(is_in_bounds(car, arena, 1, pos=(100, 10)))       # grandstands
        for outside in [(-10, 250), (250, -10), (520, 250), (250, 490)]:
            self.assertFalse(is_in_bounds(car, arena, 1, pos=outside))


class TestGates(unittest.TestCase):
    def setUp(self):
        self.finish, self.splits = load_gates(1, load_waypoints(1))

    def test_gates_found(self):
        self.assertTrue(self.finish.vertical)
        self.assertGreaterEqual(len(self.splits), 1)

    def test_race_runs_leftwards_on_the_finish_line(self):
        self.assertEqual(self.finish.sign, -1)

    def test_crossing_direction(self):
        f = self.finish
        before, after = (f.line - 5, 100), (f.line + 5, 100)
        self.assertEqual(f.crossing(before, after), f.sign)
        self.assertEqual(f.crossing(after, before), -f.sign)
        self.assertEqual(f.crossing(before, (f.line - 2, 100)), 0)

    def test_crossing_outside_the_road_does_not_count(self):
        f = self.finish
        self.assertEqual(f.crossing((f.line - 5, f.lo - 14), (f.line + 5, f.lo - 14)), 0)


class TestUserCar(unittest.TestCase):
    def setUp(self):
        self.arena = Arena(Arena_size.dims.value)
        self.car = UsrCar((250, 250), Car_colors.red)
        self.arena.spawn(self.car)

    def test_not_finished_at_start(self):
        self.assertFalse(self.car.is_finished)

    def test_accelerates_and_brakes(self):
        self.arena.tick(keys=["ArrowUp"])
        self.assertGreater(self.car.speed, 0)
        speed = self.car.speed
        self.arena.tick(keys=["ArrowDown"])
        self.assertLess(self.car.speed, speed)

    def test_steers_while_stopped(self):
        self.car._angle_cooldown = 0
        before = self.car.angle
        self.arena.tick(keys=["ArrowLeft"])
        self.assertNotEqual(self.car.angle, before)

    def test_wall_hit_bounces_and_never_traps_the_car(self):
        car = UsrCar((250, 70), Car_colors.red)
        arena = Arena(Arena_size.dims.value)
        arena.spawn(car)
        car._angle = 270.0                              # facing the top wall
        car._speed = 8.0
        arena.tick(keys=["ArrowUp"])
        self.assertTrue(car.is_bouncing)
        self.assertLess(car.speed, 0)
        for _ in range(40):
            arena.tick(keys=["ArrowUp"])
            self.assertTrue(is_in_bounds(car, arena, 1, pos=car.pos()), f"trapped at {car.pos()}")

    def test_no_control_while_bouncing(self):
        self.car.bounce_back()
        speed = self.car.speed
        self.arena.tick(keys=["ArrowUp"])
        self.assertLessEqual(self.car.speed, abs(speed))
        self.assertTrue(self.car.is_locked)


class TestItems(unittest.TestCase):
    def setUp(self):
        self.arena = Arena(Arena_size.dims.value)
        self.car = UsrCar((250, 250), Car_colors.red)
        self.arena.spawn(self.car)

    def test_wrench_is_collected_and_boosts_speed(self):
        wrench = Wrench((258, 258))
        self.arena.spawn(wrench)
        top = self.car._max_speed
        self.arena.tick(keys=[])
        self.assertEqual(self.car.wrenches, 1)
        self.assertGreater(self.car._max_speed, top)
        self.assertNotIn(wrench, self.arena.actors())

    def test_oil_puddle_makes_the_car_spin(self):
        self.arena.spawn(OilPuddle((258, 258)))
        self.arena.tick(keys=[])
        self.assertTrue(self.car.is_spinning)
        self.assertTrue(self.car.is_locked)


class TestCpuCar(unittest.TestCase):
    def test_move_works_without_arena(self):
        cpu = CpuCar((250, 250), Car_colors.yellow)
        cpu.move()

    def test_move_accepts_arena(self):
        cpu = CpuCar((250, 250), Car_colors.yellow)
        cpu.move(Arena(Arena_size.dims.value))

    def test_cpu_drives_along_the_track(self):
        game = quiet_game()
        skip_countdown(game)
        start = game.cpu_yellow.pos()
        for _ in range(300):
            game.tick([])
        cpu = game.cpu_yellow
        self.assertNotEqual(cpu.pos(), start)
        self.assertGreater(cpu.total_checkpoints_hit, 0)
        self.assertTrue(is_in_bounds(cpu, game.arena, 1, pos=cpu.pos()))


class TestRace(unittest.TestCase):
    def test_ordinal(self):
        expected = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 11: "11th", 12: "12th", 13: "13th", 21: "21st"}
        for n, text in expected.items():
            self.assertEqual(ordinal(n), text)

    def test_standings_contain_every_car_once(self):
        game = quiet_game()
        standings = game.race.standings()
        self.assertEqual(len(standings), 4)
        self.assertEqual(set(standings), set(game.race.cars))
        self.assertIn(game.race.position(game.player), (1, 2, 3, 4))


class TestGame(unittest.TestCase):
    def setUp(self):
        self.game = quiet_game()

    def test_cars_start_on_the_grid_facing_left(self):
        cars = self.game.race.cars
        self.assertEqual(len({c.pos()[0] for c in cars}), 1)
        ys = sorted(c.pos()[1] for c in cars)
        self.assertEqual([b - a for a, b in zip(ys, ys[1:])], [SuperSprintGame.START_Y_GAP] * 3)
        for car in cars:
            self.assertEqual(car.angle, 180)
            self.assertTrue(is_in_bounds(car, self.game.arena, 1))

    def test_items_and_cars_are_in_the_arena(self):
        actors = self.game.arena.actors()
        for car in self.game.race.cars:
            self.assertIn(car, actors)
        self.assertEqual(len([a for a in actors if isinstance(a, Wrench)]), len(load_items(1, "w")))
        self.assertEqual(len([a for a in actors if isinstance(a, OilPuddle)]), len(load_items(1, "p")))

    def test_game_over_and_win(self):
        self.assertFalse(self.game.game_over())
        self.assertFalse(self.game.game_won())
        self.game.player.finish(1)
        self.assertFalse(self.game.game_over())
        self.assertTrue(self.game.game_won())
        self.game.finish_delay_frames = SuperSprintGame.FPS * 5
        self.game.finish_delay_started = True
        for _ in range(SuperSprintGame.FPS * 5):
            self.game.finish_delay_frames -= 1
        self.assertTrue(self.game.game_over())

    def test_game_over_but_not_won(self):
        self.game.player.finish(3)
        self.assertFalse(self.game.game_over())
        self.assertFalse(self.game.game_won())


class TestCountdown(unittest.TestCase):
    def setUp(self):
        self.game = quiet_game()
        self.fps = SuperSprintGame.FPS

    def test_starts_at_five_seconds(self):
        self.assertTrue(self.game.is_counting_down)
        self.assertEqual(self.game.countdown_seconds, 5)

    def test_counts_down_one_number_per_second(self):
        for _ in range(self.fps):
            self.game.tick([])
        self.assertEqual(self.game.countdown_seconds, 4)

    def test_cars_stay_still_and_race_clock_is_stopped(self):
        positions = [c.pos() for c in self.game.race.cars]
        for _ in range(self.fps * 3):
            self.game.tick(["w", "ArrowUp"])
        self.assertEqual([c.pos() for c in self.game.race.cars], positions)
        self.assertEqual(self.game.player.speed, 0)
        self.assertEqual(self.game.race.frames, 0)

    def test_race_starts_after_five_seconds(self):
        for _ in range(SuperSprintGame.COUNTDOWN_SECONDS * self.fps):
            self.game.tick([])
        self.assertFalse(self.game.is_counting_down)
        self.assertEqual(self.game.countdown_seconds, 0)
        self.assertEqual(self.game.race.frames, 0)
        self.assertTrue(self.game.go_visible())
        self.game.tick([])
        self.assertEqual(self.game.race.frames, 1)

    def test_go_message_lasts_one_second(self):
        skip_countdown(self.game)
        for _ in range(self.fps):
            self.game.tick([])
        self.assertFalse(self.game.go_visible())


class TestWasd(unittest.TestCase):
    def test_map_keys_adds_arrow_equivalents(self):
        mapped = SuperSprintGame.map_keys(["w", "a", "s", "d"])
        for arrow in ["ArrowUp", "ArrowLeft", "ArrowDown", "ArrowRight"]:
            self.assertIn(arrow, mapped)
        for key in "wasd":
            self.assertIn(key, mapped)

    def test_map_keys_keeps_other_keys_and_has_no_duplicates(self):
        mapped = SuperSprintGame.map_keys(["w", "ArrowUp", "Escape"])
        self.assertEqual(mapped.count("ArrowUp"), 1)
        self.assertIn("Escape", mapped)
        self.assertEqual(SuperSprintGame.map_keys([]), [])

    def test_w_accelerates_the_player(self):
        game = quiet_game()
        skip_countdown(game)
        game.tick(["w"])
        self.assertGreater(game.player.speed, 0)

    def test_s_brakes_the_player(self):
        game = quiet_game()
        skip_countdown(game)
        game.tick(["w"])
        speed = game.player.speed
        game.tick(["s"])
        self.assertLess(game.player.speed, speed)

    def test_a_and_d_steer_the_player(self):
        for key in ("a", "d"):
            game = quiet_game()
            skip_countdown(game)
            game.player._angle_cooldown = 0
            before = game.player.angle
            game.tick([key])
            self.assertNotEqual(game.player.angle, before, key)

    def test_arrows_still_work(self):
        game = quiet_game()
        skip_countdown(game)
        game.tick(["ArrowUp"])
        self.assertGreater(game.player.speed, 0)


class TestGui(unittest.TestCase):
    def setUp(self):
        g2d.init_canvas(Arena_size.dims.value)
        self.gui = SuperSprintGui(quiet_game())

    def test_tick_draws_during_countdown(self):
        self.gui.tick()
        self.assertEqual(self.gui.game.countdown_seconds, 5)

    def test_yellow_flag_uses_sprite_animation(self):
        calls = []
        original = SuperSprintGui.draw_scaled_sprite_flag
        SuperSprintGui.draw_scaled_sprite_flag = lambda self, *args: calls.append(args)
        try:
            self.gui.game.player.start_spin()
            self.gui.draw_race_flags()
        finally:
            SuperSprintGui.draw_scaled_sprite_flag = original

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], (128, self.gui.YELLOW_FLAG_ROW))

    def test_yellow_flag_uses_sprite_animation_after_car_collision(self):
        calls = []
        original = SuperSprintGui.draw_scaled_sprite_flag
        SuperSprintGui.draw_scaled_sprite_flag = lambda self, *args: calls.append(args)
        try:
            self.gui.game.yellow_flag_frames = 30
            self.gui.draw_race_flags()
        finally:
            SuperSprintGui.draw_scaled_sprite_flag = original

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], (128, self.gui.YELLOW_FLAG_ROW))

    def test_checker_flag_uses_animation_when_first_car_finishes(self):
        calls = []
        original = SuperSprintGui.draw_scaled_sprite_flag
        SuperSprintGui.draw_scaled_sprite_flag = lambda self, *args: calls.append(args)
        try:
            self.gui.game.cpu_yellow.finish(1)
            self.gui.game.player.start_spin()
            for frame in range(SuperSprintGame.FPS):
                self.gui.game.race.frames = frame
                self.gui.draw_race_flags()
        finally:
            SuperSprintGui.draw_scaled_sprite_flag = original

        self.assertEqual(len(calls), SuperSprintGame.FPS)
        self.assertEqual({call[1][1] for call in calls}, {self.gui.CHECKER_FLAG_ROW})
        self.assertEqual(len({call[1][0] for call in calls}), self.gui.FLAG_FRAME_COUNT)


class TestCarCollisions(unittest.TestCase):
    def setUp(self):
        self.arena = Arena(Arena_size.dims.value)
        self.car1 = UsrCar((200, 200), Car_colors.red)
        self.car2 = CpuCar((205, 205), Car_colors.yellow)

    def test_collides_with_other_detects_collision(self):
        self.assertTrue(self.car1.collides_with_other(self.car2))
        self.assertTrue(self.car1.is_bouncing)
        self.assertTrue(self.car2.is_bouncing)

    def test_collides_with_other_false_when_apart(self):
        distant_car = CpuCar((300, 300), Car_colors.blue)
        self.assertFalse(self.car1.collides_with_other(distant_car))
        self.assertFalse(self.car1.is_bouncing)
        self.assertFalse(distant_car.is_bouncing)

    def test_collision_radius_boundary(self):
        # car1 center is at (208, 208)
        # Car at distance 7 (< 8) should collide
        close_car = CpuCar((200, 207), Car_colors.blue)
        self.assertTrue(self.car1.collides_with_other(close_car))

        # Car at distance 9 (>= 8, which collided under the old 16px bounding box) should not collide
        far_car = CpuCar((200, 209), Car_colors.blue)
        self.assertFalse(self.car1.collides_with_other(far_car))

    def test_check_car_collisions_cycle_in_game_tick(self):
        game = quiet_game()
        skip_countdown(game)
        # Move CPU 1 on top of CPU 2
        game.cpu_yellow._pos = game.cpu_blue._pos
        self.assertFalse(game.cpu_yellow.is_bouncing)
        self.assertFalse(game.cpu_blue.is_bouncing)
        game.tick([])
        self.assertTrue(game.cpu_yellow.is_bouncing)
        self.assertTrue(game.cpu_blue.is_bouncing)
        self.assertGreater(game.yellow_flag_frames, 0)

    def test_finished_car_collision_does_not_unfinish(self):
        self.car1.finish(1)
        self.assertTrue(self.car1.is_finished)
        self.assertTrue(self.car1.collides_with_other(self.car2))
        self.assertTrue(self.car1.is_finished)
        self.assertFalse(self.car1.is_bouncing)
        self.assertTrue(self.car2.is_bouncing)


if __name__ == "__main__":
    unittest.main()
