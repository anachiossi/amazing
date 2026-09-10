*This project has been created as part of the 42 curriculum by anade-mo, ltamiano.*

# A-Maze-ing

This project is all about mazes, generating mazes and computing
shortes paths within mazes. Every maze generated carries a block of
closed cells spelling **42**. In terms of visualization, both the
terminal as well as the GUI option are supported. The GUI option uses
the MiniLibX library (see [GUI and MiniLibX](#gui-and-minilibx)).

## Instructions

To run the project it is required to have python 3.10 or newer. Run
the following makefile commands

```bash
make install
make run RENDER=terminal
make run RENDER=gui 
```

You can also run the project directly as follows

```bash
python3 a_maze_ing.py config.txt # terminal mode
python3 a_maze_ing.py config.txt --gui # GUI mode
```

## GUI and MiniLibX

The window renderer lives in `app/render/gui/`. It uses the Python
MiniLibX wrapper (`from mlx import Mlx`). All drawing is rectangles
written into one image buffer; MiniLibX only opens the window, hands
over that buffer, blits the finished frame, and runs the event loop.

- `draw.py` — the picture (layout, rectangles, colours)
- `window.py` — MiniLibX (`Display`), keys, and animation
- `font.py` — 5x7 glyphs, painted as rectangles too

Install MiniLibX with `./mlx/init-mlx.sh` before GUI mode.

### MiniLibX APIs used

Connection and window

- mlx_init()
- mlx_get_screen_size(mlx_ptr)
- mlx_new_window(mlx_ptr, width, height, title)
- mlx_destroy_window(mlx_ptr, win_ptr)
- mlx_release(mlx_ptr)

Pixel buffer (MiniLibX "image")

- mlx_new_image(mlx_ptr, width, height)
- mlx_get_data_addr(img_ptr)
- mlx_put_image_to_window(mlx_ptr, win_ptr, img_ptr, x, y)
- mlx_do_sync(mlx_ptr)
- mlx_destroy_image(mlx_ptr, img_ptr)

Event loop and input

- mlx_expose_hook(win_ptr, callback, param)
- mlx_key_hook(win_ptr, callback, param)
- mlx_hook(win_ptr, x_event, x_mask, callback, param)
- mlx_loop_hook(mlx_ptr, callback, param)
- mlx_do_key_autorepeatoff(mlx_ptr)
- mlx_do_key_autorepeaton(mlx_ptr)
- mlx_loop(mlx_ptr)
- mlx_loop_exit(mlx_ptr)

## Configuration file

TODO

## Maze Generation Algorithms

TODO

## Shortest Path Algorithms

TODO

## The mazegen module

The library can be used to generate a maze structure and compute the
shortest path and it is independent from the app graphical aspect. It
can be installed as follows.

```bash
make build
pip install mazegen-1.0.0-py3-none-any.whl
```

An example of using the library.

```python
from mazegen import MazeConfig, MazeGenerator, MazeSolver

config = MazeConfig(20, 15, (0, 0), (19, 14), seed=7,
                    gen_algorithm="kruskal", solve_algorithm="bfs")
maze = MazeGenerator.from_config(config).generate()
path = MazeSolver.from_config(config).solve(maze)

print(maze.get_dim(), maze.get_entry(), maze.get_exit(), len(path))
maze.save("maze.txt", path)
```

## Advanced features

- Support for both terminal and GUI
- Rendering for both generation and solving animation
- Multiple algorithm for generation and solving

## Team and project management

TODO

## Resources

TODO