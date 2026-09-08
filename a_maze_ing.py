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

from app.config import MazeConfig, MazeConfigError
from app.render.terminal import (WALL_COLOURS, Drawing, TooSmallTerminal,
                                 apply_wall_colour, colour_menu, read_key,
                                 redraw, show)
from mazegen import MazeGenerator
from mazegen import MazeSolver


ACTION_BAR = "R  redraw   P  path   C  colour   Q  quit"


def message_for(drawing: Drawing, config: MazeConfig,
                seed: int | None, algorithm: str) -> list[str]:
    """The lines under the maze: how it was made, and the keys.

    Which algorithm drew it, then the size and the seed somebody
    reading the screen cannot work out for themselves, then the keys.
    """
    seed_text = seed if seed is not None else "—"
    shape = "perfect" if config.is_perfect else "braided"
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
        config = MazeConfig(sys.argv[1])
        generator = MazeGenerator.from_config(config.to_generation_config())
        maze = generator.generate()

        solver = MazeSolver.from_config(config.to_solver_config())
        path = solver.solve(maze)

        drawing = Drawing(title="A-MAZE-ING")
    except (MazeConfigError, ValueError, TooSmallTerminal) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    drawing.message = message_for(
        drawing, config, generator.config.seed, generator.name)

    try:
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
                print(colour_menu(maze, drawing))
                choice = read_key()
                if choice in "12345":
                    apply_wall_colour(drawing, WALL_COLOURS[int(choice) - 1])

    except TooSmallTerminal as error:
        # The window can be made smaller while the program is running,
        # so this is asked on every frame rather than once at the start.
        print(f"error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
