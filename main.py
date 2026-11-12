from src.lib.g2d import init_canvas, main_loop, current_keys
from src.enums import Arena_size
from src.lib.actor import Arena

arena = Arena(Arena_size.dims.value)

def main():
    init_canvas(Arena_size.dims.value)
    main_loop(tick)

def tick():
    arena.tick(current_keys())
    print(current_keys())

if __name__ == "__main__":
    print("Started main (main.py)")
    main()