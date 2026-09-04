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

import sys

from app.config import MazeConfig, MazeConfigError
from app.render.terminal import Drawing, TooSmall, show
from mazegen import MazeGenerator


def message_for(drawing: Drawing, config: MazeConfig,
                algorithm: str) -> list[str]:
    """The lines under the maze: what was asked for, and how it came out.

    ``drawing`` is read after its width is settled, and ``algorithm``
    is the one that ran, so both name what is on screen rather than
    what the config file hoped for — the file may say neither.
    """
    seed = config.seed if config.seed is not None else "—"
    shape = "perfect" if config.is_perfect else "braided"
    return [f"{config.width}x{config.height} · {shape} · seed {seed}"
            f" · {drawing.cell_width} wide",
            f"generated with {algorithm}"]


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

    # Which algorithm runs is the config file's to say, and an
    # unknown name is its mistake rather than a crash.
    try:
        generator = MazeGenerator.named(
            config.algorithm,
            width=config.width,
            height=config.height,
            entry=config.entry,
            exit=config.exit,
            perfect=config.is_perfect,
            seed=config.seed,
        )
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    maze = generator.generate()

    drawing = Drawing(title="A-MAZE-ING", fit=True)
    try:
        drawing.fit_to(maze)
    except TooSmall as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    drawing.message = message_for(drawing, config, generator.name)
    show(maze, drawing)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
