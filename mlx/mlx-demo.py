from mlx import Mlx

WIDTH, HEIGHT = 600, 600

WHITE = 0xFFFFFFFF   # 0xAARRGGBB — alpha 0xFF = opaque, 0x00 = invisible
RED   = 0xFFFF0000
GREEN = 0xFF00FF00

m = Mlx()
mlx_ptr = m.mlx_init()
win_ptr = m.mlx_new_window(mlx_ptr, WIDTH, HEIGHT, "TEST")


def draw(param=None):
    """Drawing from the expose hook means it survives resize/occlusion redraws."""
    m.mlx_clear_window(mlx_ptr, win_ptr)
    m.mlx_string_put(mlx_ptr, win_ptr, 250, 350, WHITE, "Hello world")
    # a visible 100x100 red square, one pixel at a time
    for y in range(100, 200):
        for x in range(250, 350):
            m.mlx_pixel_put(mlx_ptr, win_ptr, x, y, RED)
    # a green diagonal
    for i in range(200):
        m.mlx_pixel_put(mlx_ptr, win_ptr, 200 + i, 400 + i // 4, GREEN)


def on_key(keynum, param):
    if keynum == 65307:   # ESC (keynums are X keysyms: space is 32, 'a' is 97)
        m.mlx_loop_exit(mlx_ptr)


def on_close(param):
    m.mlx_loop_exit(mlx_ptr)


m.mlx_expose_hook(win_ptr, draw, None)
m.mlx_key_hook(win_ptr, on_key, None)
m.mlx_hook(win_ptr, 33, 0, on_close, None)   # 33 = window close button

m.mlx_loop(mlx_ptr)
