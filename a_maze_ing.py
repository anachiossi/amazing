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

The window answers three lines of keys: R for a new maze, P for the
path, the arrows for the entry, Q to leave; C and F cycle colours; G
and S cycle the generator and the solver, A and V whether those run
as an animation. The terminal keeps R, P, C and Q.
"""

import random
import sys
from collections.abc import Mapping

from app.config import MazeConfigError, read_config
from app.render import gui
from app.render.terminal import (WALL_COLOURS, Drawing, TooSmallTerminal,
                                 apply_wall_colour, colour_menu, read_key,
                                 redraw, show)
from mazegen import (Direction, Maze, MazeConfig, MazeGenerator,
                     MazeSolver, Path)

ACTION_BAR = "R  redraw   P  path   C  colour   Q  quit"

TITLE = "A-MAZE-ING"

NO_MLX = ("this build has no MiniLibX: run ./mlx/init-mlx.sh to install "
          "it, or leave --gui out and draw the maze in the terminal")

# Arrow keys move the entry one cell. Named the same way ``key_letter``
# reports them, so the window can hand the tap through unchanged.
ARROW = {
    "left": Direction.W,
    "right": Direction.E,
    "up": Direction.N,
    "down": Direction.S,
}


def moved_entry(maze: Maze, key: str) -> tuple[int, int] | None:
    """The cell one step that way from the entry, or None if it cannot go.

    A wall on that side stops it, as does the edge of the maze. The
    exit and the cells of the "42" are not places a route should start.
    """
    side = ARROW.get(key)
    if side is None:
        return None
    here = maze.get_entry()
    if here is None:
        return None
    col, row = here
    if maze.get_wall(col, row, side):
        return None
    there = maze.across(col, row, side)
    if there not in maze:
        return None
    if there == maze.get_exit() or there in maze.get_frozen():
        return None
    return there


def next_named(registry: Mapping[str, object], current: str) -> str:
    """The name after ``current`` in that registry, wrapping around."""
    names = sorted(registry)
    if not names:
        return current
    if current not in names:
        return names[0]
    return names[(names.index(current) + 1) % len(names)]


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
                algorithm: str, solver: str) -> list[str]:
    """The lines under the maze: how it was made, and the keys.

    A short window gives these up from the top, so the order is the
    order they can be lost in: what ``describes`` says first goes
    first, and the keys are never given up at all.
    """
    return [*describes(config, algorithm, solver),
            f"{drawing.cell_width} wide",
            ACTION_BAR]


def in_terminal(config: MazeConfig, generator: MazeGenerator,
                solver: MazeSolver, output_file: str) -> int:
    """Draw the maze in the terminal, and run until the user quits."""
    maze = generator.generate()
    path = solver.solve(maze)
    write_out(maze, path, output_file)

    drawing = Drawing(title=TITLE)
    drawing.message = message_for(
        drawing, config, generator.name, solver.name)

    try:
        if not sys.stdin.isatty():
            show(maze, drawing)
            return 0

        while True:
            drawing.message = message_for(
                drawing, config, generator.name, solver.name)
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
                write_out(maze, path, output_file)
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
              solver: MazeSolver, output_file: str) -> int:
    """Draw the maze in a window, and let MLX run until it is closed.

    A window cannot be driven the way the terminal loop above drives
    itself, because MLX keeps the loop. So what R, G and S do to the
    maze is handed over as a function and the window calls it.
    """
    maze = generator.generate()

    def make_scene(current: Maze) -> gui.Scene:
        route = solver.solve(current)
        write_out(current, route, output_file)
        return gui.Scene(current, route, TITLE,
                         describes(config, generator.name, solver.name))

    def finish(current: Maze) -> gui.Scene:
        nonlocal maze
        maze = current
        return make_scene(maze)

    def on_maze(key: str, animate: bool = False
                ) -> gui.Scene | gui.Playback | None:
        nonlocal generator, solver, maze
        if key in ("r", "g"):
            if key == "g":
                config.gen_algorithm = next_named(
                    MazeGenerator.algorithms, generator.name)
                generator = MazeGenerator.from_config(config)
            else:
                generator.config.seed = random.randrange(1 << 30)
            if animate:
                return gui.Playback(generator.carve(), finish)
            maze = generator.generate()
            return make_scene(maze)
        if key == "s":
            config.solve_algorithm = next_named(
                MazeSolver.algorithms, solver.name)
            solver = MazeSolver.from_config(config)
            return make_scene(maze)
        there = moved_entry(maze, key)
        if there is None:
            return None
        maze.set_entry(there)
        config.entry_cell = there
        return make_scene(maze)

    gui.show(make_scene(maze), on_maze=on_maze)
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
        config, output_file = read_config(arguments[0])
        generator = MazeGenerator.from_config(config)
        solver = MazeSolver.from_config(config)
        if window:
            return in_window(config, generator, solver, output_file)
        return in_terminal(config, generator, solver, output_file)
    except (MazeConfigError, ValueError, OSError,
            TooSmallTerminal, gui.TooSmall) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except ImportError:
        print(f"error: {NO_MLX}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
