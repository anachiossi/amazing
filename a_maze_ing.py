#!/usr/bin/env python3
"""Entry point: ``python3 a_maze_ing.py config.txt``.

This file is the glue between the three parts that do not know each
other: the configuration, the maze, and the renderer.

Choosing how big a cell is drawn belongs here, and nowhere else. The
maze has no idea it will be looked at, and the renderer draws at
whatever scale it is handed — "draw this maze this big" is all it
knows. What is left, working out what actually fits on the screen in
front of the user, is glue, so it lives with the other glue.
"""

import random
import shutil
import sys

from app.config import MazeConfig, MazeConfigError
from app.render.terminal import (BLOCKS, FRAME, STANDARD_SKIN, Drawing,
                                 TerminalSkin, TooSmall, show,
                                 widest_that_fits)
from mazegen import Maze

# Below this, the box-drawing walls have nowhere to go and the blocks
# skin takes over. Everything else about size is the renderer's.
COMPACT = 2


def skin_for(cell_width: int) -> TerminalSkin:
    """Return the skin that suits a cell of that width.

    The only decision left here: at one character wide a cell has no
    room for the box-drawing lines to read, so the walls become solid
    blocks. Which sizes exist and how big a drawing is are the
    renderer's business — ``widest_that_fits`` answers that.
    """
    return STANDARD_SKIN if cell_width >= COMPACT else BLOCKS


def main() -> int:
    """Read the config, build a maze, and draw it at the size that fits."""
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py config.txt", file=sys.stderr)
        return 1
    file_path: str = sys.argv[1]
    # Only the call that can fail is wrapped, so a bug further down is
    # not mistaken for a bad configuration file.
    try:
        config = MazeConfig(file_path)
    except MazeConfigError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    # There is no generator yet, so the walls come from randomize():
    # a board with no connectivity, which is enough to look at.
    random.seed(42 if config.seed is None else config.seed)
    maze = Maze(config.width, config.height)
    maze.randomize(0.35)

    try:
        cell_width = widest_that_fits(config.width, config.height,
                                      shutil.get_terminal_size(), FRAME)
    except TooSmall as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    tier = {3: "full", COMPACT: "compact"}.get(cell_width, "blocks")
    show(maze, Drawing(
        entry=config.entry,
        exit=config.exit,
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
