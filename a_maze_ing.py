#!/usr/bin/env python3
"""Entry point: ``python3 a_maze_ing.py config.txt``.

This file is the glue between the parts that do not know each other:
the configuration, the maze, and the renderer that draws it.

The maze has no idea it will be looked at. The renderer knows the
surface it draws on — how wide a cell can be, and how much room the
whole thing takes — and it refuses a maze that cannot be drawn where
it draws. What is left here is the one thing it cannot decide: what
should happen when the answer is that the maze does not fit at all.

The terminal answers R for a new maze, P for the path, C for colour,
A for animation, and Q to leave.
"""

import random
import sys
from dataclasses import replace

from app.config import MazeConfigError, read_config
from app.render.terminal import (CARVE_DELAY, CARVE_EVERY, PATH_DELAY,
                                 WALL_COLOURS,
                                 Drawing, TooSmallTerminal, animate,
                                 apply_wall_colour, colour_menu, read_key,
                                 redraw, show)
from mazegen import Maze, MazeConfig, MazeGenerator, MazeSolver, Path

TITLE = "A-MAZE-ING"

ANIMATION = True


def action_bar(animating: bool) -> str:
    """The action bar for the terminal."""
    state = "on" if animating else "off"
    return f"R  redraw   P  path   C  colour   Q  quit   A  animate ({state})"


def describes(config: MazeConfig, algorithm: str, solver: str) -> list[str]:
    """What a reader cannot work out by looking at the drawing.

    Which algorithms built and solved it, and how large it is: three
    facts the maze itself does not write on the walls.
    """
    return [f"generation: {algorithm}",
            f"solver: {solver}",
            f"resolution: {config.width}x{config.height}"]


def write_out(maze: Maze, route: Path, output_file: str) -> None:
    """Write the maze the subject asks for, replacing the last file.

    The grid, the ends and the shortest path: one file, the format
    IV.5 names, so a later run overwrites rather than appends.
    """
    maze.save(output_file, route)


def message_for(drawing: Drawing, config: MazeConfig,
                algorithm: str, solver: str,
                animating: bool) -> list[str]:
    """The lines under the maze: how it was made, and the keys.

    A short window gives these up from the top, so the order is the
    order they can be lost in: what ``describes`` says first goes
    first, and the keys are never given up at all.
    """
    lines = describes(config, algorithm, solver)
    lines.append(f"{drawing.cell_width} wide")
    lines.append(action_bar(animating))
    return lines


def in_terminal(config: MazeConfig, generator: MazeGenerator,
                solver: MazeSolver, output_file: str) -> int:
    """Draw the maze in the terminal, and run until the user quits."""
    if generator.config.seed is None:
        generator.config.seed = random.randrange(1 << 30)
    maze = generator.generate()
    path = solver.solve(maze)
    write_out(maze, path, output_file)

    animating = ANIMATION
    drawing = Drawing(title=TITLE)
    drawing.message = message_for(
        drawing, config, generator.name, solver.name, animating)

    try:
        if not sys.stdin.isatty():
            show(maze, drawing)
            return 0
        if animating:
            animate(generator.carve(), replace(drawing, paths=()),
                    delay=CARVE_DELAY, every=CARVE_EVERY)
            maze = generator.maze

        while True:
            drawing.message = message_for(
                drawing, config, generator.name, solver.name, animating)
            redraw(maze, drawing)

            key = read_key()
            if key in ("a", "A"):
                animating = not animating
            if key in ("q", "Q", "\x03", "\x1b"):
                break
            if key in ("r", "R"):
                generator.config.seed = random.randrange(1 << 30)
                if animating:
                    animate(generator.carve(), replace(drawing, paths=()),
                            delay=CARVE_DELAY, every=CARVE_EVERY)
                    maze = generator.maze
                else:
                    maze = generator.generate()
                # A new maze is a new way through it, so the route is
                # asked for again whether or not it is on screen: turning
                # it on later would otherwise draw the old maze's path.
                path = solver.solve(maze)
                write_out(maze, path, output_file)
                if drawing.paths:
                    drawing.paths = (path,)
            if key in ("p", "P"):
                if drawing.paths:
                    drawing.paths = ()
                else:
                    drawing.paths = (path,)
                    if animating:
                        animate((maze,), drawing, delay=PATH_DELAY)
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


def main() -> int:
    """Read the config, then draw the maze in the terminal."""
    arguments = sys.argv[1:]
    if len(arguments) != 1:
        print("Usage: python3 a_maze_ing.py config.txt", file=sys.stderr)
        return 1

    try:
        config, output_file = read_config(arguments[0])
        generator = MazeGenerator.from_config(config)
        solver = MazeSolver.from_config(config)
        return in_terminal(config, generator, solver, output_file)
    except (MazeConfigError, ValueError, OSError,
            TooSmallTerminal) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
