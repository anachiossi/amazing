#!/usr/bin/env python3
"""Entry point: ``python3 a_maze_ing.py config.txt``.

This file is the glue between the three parts that do not know each
other: the configuration, the maze, and the renderer.

The maze has no idea it will be looked at, and the renderer knows the
terminal it draws into — how wide a cell can be, which skin suits that
width, and how much room the whole thing takes. What is left here is
the one thing neither of them can decide: what should happen when the
maze does not fit at all. This file answers that with a message and a
non-zero exit.
"""

import random
import sys

from app.config import MazeConfigError, read_config
from app.render.terminal import (WALL_COLOURS, Drawing, TooSmall,
                                 apply_wall_colour, palette_line,
                                 read_key, redraw, show)
from mazegen import MazeConfig, MazeGenerator, MazeSolver


ACTION_BAR = "R  redraw   P  path   C  colour   Q  quit"


def message_for(drawing: Drawing, config: MazeConfig,
                seed: int | None, algorithm: str) -> list[str]:
    """The lines under the maze, least worth keeping first.

    A short window gives these up from the top, so the order is the
    order they can be lost in: which algorithm drew it is a thing the
    defence can be told out loud, the size and the seed are what
    somebody reading the screen cannot work out for themselves, and
    the keys are never given up at all.
    """
    seed_text = seed if seed is not None else "—"
    shape = "perfect" if config.perfect else "braided"
    return [f"generated with {algorithm}",
            f"{config.width}x{config.height} · {shape} · seed {seed_text}"
            f" · {drawing.cell_width} wide",
            ACTION_BAR]


def main() -> int:
    """Read the config, then run until the user quits."""
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py config.txt", file=sys.stderr)
        return 1

    try:
        config, _output_file = read_config(sys.argv[1])
        generator = MazeGenerator.from_config(config)
        maze = generator.generate()

        solver = MazeSolver.from_config(config)
        path = solver.solve(maze)

        drawing = Drawing(title="A-MAZE-ING", fit=True)
        # Said before it is asked whether it fits: the lines under the
        # maze are part of what has to fit, and a window too short for
        # them is what the fit gives the title up for.
        drawing.message = message_for(
            drawing, config, generator.config.seed, generator.name)
        drawing.fit_to(maze)
    except (MazeConfigError, ValueError, TooSmall) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    drawing.message = message_for(
        drawing, config, generator.config.seed, generator.name)

    if not sys.stdin.isatty():
        show(maze, drawing)
        return 0

    while True:
        drawing.message = message_for(
            drawing, config, generator.config.seed, generator.name)
        redraw(maze, drawing)

        key = read_key()
        if key in ("q", "Q", "\x03", "\x1b"):
            break
        if key in ("r", "R"):
            generator.config.seed = random.randrange(1 << 30)
            maze = generator.generate()
            # A new maze is a new way through it, so the route is
            # asked for again whether or not it is on screen: turning
            # it on later would otherwise draw the old maze's path.
            path = solver.solve(maze)
            if drawing.paths:
                drawing.paths = (path,)
        if key in ("p", "P"):
            if drawing.paths:
                drawing.paths = ()
            else:
                drawing.paths = (path,)
        if key in ("c", "C"):
            print(palette_line(maze, drawing))
            choice = read_key()
            if choice in "12345":
                apply_wall_colour(drawing, WALL_COLOURS[int(choice) - 1])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
