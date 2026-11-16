import unittest
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame as pg
from src.lib.actor import Arena
from src.enums import Arena_size, Car_colors, Car_size
from src.classes import UsrCar, Car, CurvedWall, ExternalWall, InternalWall, CpuCar
from src.funcs import (
    is_wall,
    get_cached_walls,
    is_in_bounds,
    init_arena,
    draw_walls,
    draw_actor,
    draw_debug_info,
    load_waypoints,
    actor_center,
    clamp
)
from src.lib import g2d

class TestSuperSprintFixes(unittest.TestCase):
    def setUp(self):
        self.arena = Arena(Arena_size.dims.value)
        self.walls = get_cached_walls(1)

    def test_arena_size(self):
        """Test that Arena_size matches 512x480 (64x60 blocks of 8x8)."""
        self.assertEqual(Arena_size.width.value, 512)
        self.assertEqual(Arena_size.height.value, 480)
        self.assertEqual(Arena_size.dims.value, (512, 480))
        self.assertEqual(self.arena.size(), (512, 480))

    def test_map_integrity(self):
        """Test that lvl-1.txt has exactly 60 rows and 64 columns."""
        self.assertEqual(len(self.walls), 60)
        for r, row in enumerate(self.walls):
            self.assertEqual(len(row), 64, f"Row {r} length is {len(row)}, expected 64")
        # Check outer walls
        self.assertTrue(all(self.walls[0][c] == '#' for c in range(64)))
        self.assertTrue(all(self.walls[59][c] == '#' for c in range(64)))
        self.assertTrue(all(self.walls[r][0] == '#' for r in range(60)))
        self.assertTrue(all(self.walls[r][63] == '#' for r in range(60)))

    def test_asset_paths_exist(self):
        """Test that image paths resolve locally and files exist on disk."""
        car = UsrCar((250, 250), Car_colors.red)
        img_path, clip_pos, clip_size = car.get_sprite_cutout()
        self.assertTrue(os.path.exists(img_path), f"Car spritesheet not found: {img_path}")
        self.assertEqual(clip_size, (16, 16))

        bg_path = os.path.join(os.path.dirname(__file__), "src", "img", "super-sprint-bg.png")
        self.assertTrue(os.path.exists(bg_path), f"Background not found: {bg_path}")

    def test_is_finished_no_recursion(self):
        """Test that is_finished does not cause recursion error."""
        car = UsrCar((250, 250), Car_colors.red)
        self.assertFalse(car.is_finished)

    def test_is_in_bounds_positions(self):
        """Test is_in_bounds on road vs wall vs outside arena."""
        car = UsrCar((250, 250), Car_colors.red)
        # (250, 250) is on the open road
        self.assertTrue(is_in_bounds(car, self.arena, 1, pos=(250, 250)))

        # Grandstands (top area y=10) is wall
        self.assertFalse(is_in_bounds(car, self.arena, 1, pos=(100, 10)))

        # Outside arena
        self.assertFalse(is_in_bounds(car, self.arena, 1, pos=(-10, 250)))
        self.assertFalse(is_in_bounds(car, self.arena, 1, pos=(250, -10)))
        self.assertFalse(is_in_bounds(car, self.arena, 1, pos=(520, 250)))
        self.assertFalse(is_in_bounds(car, self.arena, 1, pos=(250, 490)))

    def test_steering_when_stopped(self):
        """Test that UsrCar can steer when speed is 0."""
        car = UsrCar((250, 250), Car_colors.red)
        car._speed = 0.0
        initial_angle = car.angle

        self.arena.spawn(car)
        car._angle_cooldown = 0
        self.arena.tick(keys=["ArrowLeft"])

        # Car should have changed angle even with speed 0
        self.assertNotEqual(car.angle, initial_angle)

    def test_collision_prevents_penetration_and_allows_escape(self):
        """Test that collision does not trap the car inside a wall."""
        car = UsrCar((250, 70), Car_colors.red)
        self.arena.spawn(car)
        self.assertTrue(is_in_bounds(car, self.arena, 1, pos=car.pos()))

        # Face UP (angle 270 in polar coords) towards top wall
        car._angle = 270.0
        car._speed = 8.0

        for _ in range(20):
            self.arena.tick(keys=["ArrowUp"])

        # The car MUST NOT be inside the wall!
        self.assertTrue(is_in_bounds(car, self.arena, 1, pos=car.pos()),
                        f"Car got trapped inside wall at pos {car.pos()}")

        # Now test escape: turn down and accelerate
        car._angle = 90.0
        car._speed = 0.0

        for _ in range(10):
            self.arena.tick(keys=["ArrowUp"])

        self.assertGreater(car.pos()[1], 70.0)
        self.assertTrue(is_in_bounds(car, self.arena, 1, pos=car.pos()))

    def test_multidirectional_bounce(self):
        """Test that hitting walls at various angles bounces cleanly without getting stuck."""
        for angle in [0.0, 45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0]:
            arena = Arena(Arena_size.dims.value)
            car = UsrCar((250, 250), Car_colors.red)
            arena.spawn(car)
            car._angle = angle
            car._speed = 10.0

            hit_wall = False
            for _ in range(50):
                arena.tick(keys=["ArrowUp"])
                if car._speed < 0:
                    hit_wall = True
                    break

            self.assertTrue(hit_wall, f"Car never hit wall moving at angle {angle}")
            self.assertTrue(is_in_bounds(car, arena, 1, pos=car.pos()),
                            f"Car ended inside wall at angle {angle}: {car.pos()}")

    def test_draw_walls_and_rendering(self):
        """Test that draw_walls, draw_debug_info and init_arena execute on canvas without error."""
        g2d.init_canvas(Arena_size.dims.value)
        init_arena(1)
        draw_walls(lvl=1)
        car = UsrCar((250, 250), Car_colors.red)
        draw_actor(car)
        draw_debug_info(car, lvl=1)

    def test_load_waypoints(self):
        """Test that load_waypoints finds all @ points in lvl-1.txt and orders them."""
        wps = load_waypoints(1)
        self.assertGreaterEqual(len(wps), 10, "Expected at least 10 waypoints in map")
        # Ensure all waypoints are in bounds
        car = UsrCar((0, 0), Car_colors.yellow)
        for i, wp in enumerate(wps):
            # Tile center to top-left
            car_pos = (wp[0] - 8, wp[1] - 8)
            self.assertTrue(is_in_bounds(car, self.arena, 1, pos=car_pos),
                            f"Waypoint {i+1} at {wp} collides with wall!")

    def test_starting_grid_side_by_side(self):
        """Test that all 4 cars start side by side at the start line facing left."""
        wps = load_waypoints(1)
        grid = [
            (Car_colors.yellow, (175, 338)),
            (Car_colors.blue,   (175, 354)),
            (Car_colors.red,    (175, 370)),
            (Car_colors.white,  (175, 386)),
        ]
        cars = []
        for col, pos in grid:
            car = CpuCar(pos, col, waypoints=wps) if col != Car_colors.red else UsrCar(pos, col)
            car._angle = 180.0
            cars.append(car)
            self.assertTrue(is_in_bounds(car, self.arena, 1, pos=pos),
                            f"Start position {pos} for {col.name} is blocked!")
            self.assertEqual(car.angle, 180.0)

        # Check they have same X coordinate (side-by-side on vertical grid line)
        xs = [c.pos()[0] for c in cars]
        self.assertTrue(all(x == xs[0] for x in xs))
        # Check ascending Y positions with spacing
        ys = [c.pos()[1] for c in cars]
        for i in range(len(ys) - 1):
            self.assertEqual(ys[i+1] - ys[i], 16)

    def test_cpu_car_waypoint_driving(self):
        """Test that CpuCar autonomously follows waypoints around the track."""
        wps = load_waypoints(1)
        cpu = CpuCar((175, 338), Car_colors.yellow, waypoints=wps, max_speed=5.0)
        self.arena.spawn(cpu)

        initial_pos = cpu.pos()
        # Run 500 ticks
        for _ in range(500):
            self.arena.tick()

        # The car must have driven along waypoints and advanced
        self.assertNotEqual(cpu.pos(), initial_pos)
        self.assertGreater(cpu.total_checkpoints_hit, 0)
        self.assertTrue(is_in_bounds(cpu, self.arena, 1, pos=cpu.pos()),
                        f"CpuCar ended out of bounds: {cpu.pos()}")

    def test_curved_wall_methods(self):
        """Test that CurvedWall center() call does not raise TypeError."""
        ext_wall = ExternalWall((0, 0), (100, 100), (50, 50), 40.0)
        car = UsrCar((250, 250), Car_colors.red)
        result = ext_wall.confirm_collision(car)
        self.assertIsInstance(result, bool)

    def test_cpu_car_move_signature(self):
        """Test that CpuCar.move accepts arena."""
        cpu = CpuCar((250, 250), Car_colors.yellow)
        try:
            cpu.move(self.arena)
        except Exception as e:
            self.fail(f"CpuCar.move raised: {e}")

if __name__ == "__main__":
    unittest.main()
