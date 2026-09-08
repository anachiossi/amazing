#!/usr/bin/env python3
"""Entry point: ``python3 a_maze_ing.py config.txt [--gui]``.

This file is the glue between the parts that do not know each other:
the configuration, the maze, and whichever renderer draws it.

The maze has no idea it will be looked at. The two renderers know the
surface they draw on — the terminal knows how wide a cell can be and
how much room the whole thing takes, the window knows how many pixels
the screen has — and both of them refuse a maze that cannot be drawn
where they draw. What is left here is the one thing none of them can
decide: which of the two to open, and what should happen when the
answer is that the maze does not fit at all.

Both renderings answer the same keys for the same things — R for a new
maze, P for the path, C for the colour of the walls, Q to leave.
"""

import random
import sys

from app.config import MazeConfigError, read_config
from app.render import gui
from app.render.terminal import (WALL_COLOURS, Drawing, TooSmallTerminal,
                                 apply_wall_colour, colour_menu, read_key,
                                 redraw, show)
from mazegen import MazeConfig, MazeGenerator, MazeSolver

ACTION_BAR = "R  redraw   P  path   C  colour   Q  quit"

TITLE = "A-MAZE-ING"

NO_MLX = ("this build has no MiniLibX: run ./mlx/init-mlx.sh to install "
          "it, or leave --gui out and draw the maze in the terminal")


def describes(config: MazeConfig, seed: int | None,
              algorithm: str) -> list[str]:
    """What a reader cannot work out by looking at the drawing.

    Which algorithm carved it can be told out loud at the defence; the
    size and the seed are the two things the screen cannot show, and
    the seed is the one that makes a maze come back.
    """
    seed_text = seed if seed is not None else "—"
    shape = "perfect" if config.perfect else "braided"
    return [f"generated with {algorithm}",
            f"{config.width}x{config.height} · {shape} · seed {seed_text}"]


def message_for(drawing: Drawing, config: MazeConfig,
                seed: int | None, algorithm: str) -> list[str]:
    """The lines under the maze: how it was made, and the keys.

    A short window gives these up from the top, so the order is the
    order they can be lost in: what ``describes`` says first goes
    first, and the keys are never given up at all.
    """
    algorithm_line, maze_line = describes(config, seed, algorithm)
    return [algorithm_line,
            f"{maze_line} · {drawing.cell_width} wide",
            ACTION_BAR]


def in_terminal(config: MazeConfig, generator: MazeGenerator,
                solver: MazeSolver) -> int:
    """Draw the maze in the terminal, and run until the user quits."""
    maze = generator.generate()
    path = solver.solve(maze)

    drawing = Drawing(title=TITLE)
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


def in_window(config: MazeConfig, generator: MazeGenerator,
              solver: MazeSolver) -> int:
    """Draw the maze in a window, and let MLX run until it is closed.

    A window cannot be driven the way the terminal loop above drives
    itself, because MLX keeps the loop. So what a new maze *is* is
    handed over as a function and the window calls it when R is
    pressed — which is the whole of what this has to say.
    """
    def scene() -> gui.Scene:
        maze = generator.generate()
        return gui.Scene(maze, solver.solve(maze), TITLE,
                         describes(config, generator.config.seed,
                                   generator.name))

    def another() -> gui.Scene:
        generator.config.seed = random.randrange(1 << 30)
        return scene()

    gui.show(scene(), new_scene=another)
    return 0


def main() -> int:
    """Read the config, then draw the maze where it was asked for."""
    arguments = [word for word in sys.argv[1:] if word != "--gui"]
    window = "--gui" in sys.argv[1:]
    if len(arguments) != 1:
        print("Usage: python3 a_maze_ing.py config.txt [--gui]",
              file=sys.stderr)
        return 1

    try:
        config, _output_file = read_config(arguments[0])
        generator = MazeGenerator.from_config(config)
        solver = MazeSolver.from_config(config)
        if window:
            return in_window(config, generator, solver)
        return in_terminal(config, generator, solver)
    except (MazeConfigError, ValueError,
            TooSmallTerminal, gui.TooSmall) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except ImportError:
        print(f"error: {NO_MLX}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
