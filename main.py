from src.lib.g2d import init_canvas, main_loop
from src.main_loop import tick
from src.enums import Arena_size

def main():
    init_canvas(Arena_size.dims.value)
    main_loop(tick)

if __name__ == "__main__":
    print("Started main (main.py)")
    main()