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
from app.render.terminal import Drawing, TooSmall, show
from mazegen import Maze


def message_for(drawing: Drawing, config: MazeConfig) -> list[str]:
    """The lines under the maze: what was asked for, and how it came out.

    ``drawing`` is read after its width is settled, so the size named
    here is the size on screen rather than the size hoped for.
    """
    seed = config.seed if config.seed is not None else "—"
    shape = "perfect" if config.is_perfect else "braided"
    return [f"{config.width}x{config.height} · {shape} · seed {seed}"
            f" · {drawing.cell_width} wide",
            "walls are randomize() for now — no generator yet"]


def main() -> int:
    """Read the config, build a maze, and draw it at the size that fits."""
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py config.txt", file=sys.stderr)
        return 1
    file_path: str = sys.argv[1]

    # Read parameters for maze generation
    try:
        config = MazeConfig(file_path)
    except MazeConfigError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    # There is no generator yet, so the walls come from randomize():
    # a board with no connectivity, which is enough to look at.
    random.seed(42 if config.seed is None else config.seed)
    maze = Maze(config.width, config.height, config.entry, config.exit)
    maze.randomize(0.35)

    drawing = Drawing(title="A-MAZE-ING", fit=True)
    try:
        drawing.fit_to(maze)
    except TooSmall as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    drawing.message = message_for(drawing, config)
    show(maze, drawing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
