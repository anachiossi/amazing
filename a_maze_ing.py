#!/usr/bin/env python3
"""Entry point: ``python3 a_maze_ing.py config.txt``.

This file is the glue between the three parts that do not know each
other: the configuration, the maze, and the renderer.

The maze has no idea it will be looked at, and the renderer draws at
whatever scale it is handed. What is left is the part neither of them
can answer: how much room there actually is on the screen in front of
the user, and what to do when there is not enough. Reading the
terminal and giving up with an error are both this file's, so the
arithmetic they feed stays testable without a terminal to run in.
"""

import random
import shutil
import sys

from app.config import MazeConfig, MazeConfigError
from app.render.terminal import (COMPACT, FRAME, Drawing, TooSmall, show,
                                 skin_for, widest_that_fits)
from mazegen import Maze


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

    try:
        cell_width = widest_that_fits(config.width, config.height,
                                      shutil.get_terminal_size(), FRAME)
    except TooSmall as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    tier = {3: "full", COMPACT: "compact"}.get(cell_width, "blocks")
    show(maze, Drawing(
        title="A-MAZE-ING",
        message=[f"{config.width}x{config.height} · "
                 f"{'perfect' if config.is_perfect else 'braided'} · "
                 f"seed {config.seed if config.seed is not None else '—'}"
                 f" · {tier} ({cell_width} wide)",
                 "walls are randomize() for now — no generator yet"],
        skin=skin_for(cell_width),
        cell_width=cell_width,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
