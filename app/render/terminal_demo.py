"""A tour of the terminal renderer:  python3 -m app.render.terminal_demo

The renderer drawing a maze, a maze being carved, then the same
maze animated. It
lives beside the renderer rather than inside it: nothing here is part
of drawing a maze, and the route below is a stand-in for a solver that
does not exist yet.
"""

import random
from dataclasses import replace

from mazegen import Maze, MazeGenerationConfig, MazeGenerator

from .terminal import STANDARD_SKIN, Drawing, animate, show


def main() -> None:
    """Draw a maze, then animate the way through it.

    The maze is Leo's ``randomize()``: every wall thrown on its own,
    with no promise that anywhere can be reached from anywhere. Seed
    168 is one where the two corners happen to be joined, and the way
    between them is written out below — until there is a solver to ask,
    a route has to be known in advance to be drawn.
    """
    random.seed(168)
    entry, exit = (0, 0), (9, 4)
    maze = Maze(10, 5, entry, exit)
    maze.randomize(0.35)

    # The way from one corner to the other through that maze. It holds
    # only for seed 168 at that size: change either and it is nonsense,
    # which is what a solver will save us from.
    solved = [(0, 0), (1, 0), (1, 1), (1, 2), (2, 2), (2, 3), (2, 4),
              (3, 4), (3, 3), (3, 2), (4, 2), (4, 1), (5, 1), (6, 1),
              (7, 1), (7, 0), (8, 0), (9, 0), (9, 1), (9, 2), (9, 3),
              (9, 4)]

    caption = "walls, symbols, room to breathe"
    print(f"\n{caption}\n")
    show(maze, Drawing(paths=[solved], title="A-MAZE-ING",
                       message=[caption], skin=STANDARD_SKIN,
                       cell_width=3))

    try:
        input("\npress enter to run the animations ")
    except EOFError:
        # Nothing on the input: the drawings above are all that was
        # wanted.
        return

    # The generator carving, which is the one beat where the "42"
    # arrives. It is sealed before the first wall comes down, and the
    # renderer holds its colour back until the maze around each of its
    # cells is carved — so the shape is never drawn, it is uncovered.
    #
    # Its own maze, and the smallest the shape fits in: the one above
    # is 10x5 and carries a route written out by hand for seed 168.
    carving = MazeGenerationConfig(11, 9, (0, 0), (10, 8),
                                   perfect=False, seed=3)
    generator = MazeGenerator.from_config(carving)
    plan = Drawing(title="A-MAZE-ING", fit=True,
                   message=["carving — the 42 comes out of the maze"])
    animate(generator.carve(), plan, delay=0.05)
    animate((generator.maze,),
            replace(plan, message=["carved — and the 42 it left behind"]),
            delay=2.0, reveal=False)

    # The maze stands with its two ends; then one search walks it; then
    # two do, from both ends at once. Back to the 10x5 one: it is the
    # route through it that the searches below walk.
    ends = Drawing(title="A-MAZE-ING",
                   message=["the way in, and the way out"])
    animate((maze,), ends, delay=1.0)

    animate((maze,), replace(ends, paths=[solved],
                             message=["one search, from the entry"]),
            delay=0.12)
    animate((maze,), replace(ends, paths=[solved], message=["solved"]),
            delay=1.5, reveal=False)

    half = len(solved) // 2 + 1
    from_entry, from_exit = solved[:half], solved[half - 1:][::-1]
    animate((maze,), replace(ends, paths=[from_entry, from_exit],
                             message=["two searches, meeting in the "
                                      "middle"]), delay=0.12)
    animate((maze,), replace(ends, paths=[from_entry, from_exit, solved],
                             message=["solved"]),
            delay=0.0, reveal=False)


if __name__ == "__main__":
    main()
