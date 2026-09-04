"""A tour of the terminal renderer:  python3 -m app.render.demo

Every size the renderer draws at, then the same maze animated. It
lives beside the renderer rather than inside it: nothing here is part
of drawing a maze, and the route below is a stand-in for a solver that
does not exist yet.
"""

import random
from dataclasses import replace

from mazegen import Maze

from .terminal import BLOCKS, STANDARD_SKIN, Drawing, animate, show


def main() -> None:
    """Draw a maze at each size, then animate the way through it.

    The maze is Leo's ``randomize()``: every wall thrown on its own,
    with no promise that anywhere can be reached from anywhere. Seed
    168 is one where the two corners happen to be joined, and the way
    between them is written out below — until there is a solver to ask,
    a route has to be known in advance to be drawn.
    """
    random.seed(168)
    maze = Maze(10, 5)
    maze.randomize(0.35)
    entry, exit = (0, 0), (9, 4)

    # The way from one corner to the other through that maze. It holds
    # only for seed 168 at that size: change either and it is nonsense,
    # which is what a solver will save us from.
    solved = [(0, 0), (1, 0), (1, 1), (1, 2), (2, 2), (2, 3), (2, 4),
              (3, 4), (3, 3), (3, 2), (4, 2), (4, 1), (5, 1), (6, 1),
              (7, 1), (7, 0), (8, 0), (9, 0), (9, 1), (9, 2), (9, 3),
              (9, 4)]

    for caption, cell_width, skin in (
            ("full — walls, symbols, room to breathe", 3, STANDARD_SKIN),
            ("compact — the same, tighter", 2, STANDARD_SKIN),
            ("blocks — a cell is one character", 1, BLOCKS)):
        print(f"\n{caption}\n")
        show(maze, Drawing(entry=entry, exit=exit, paths=[solved],
                           title="A-MAZE-ING", message=[caption],
                           skin=skin, cell_width=cell_width))

    try:
        input("\npress enter to run the animations ")
    except EOFError:
        # Nothing on the input: the drawings above are all that was
        # wanted.
        return

    # The maze stands with its two ends; then one search walks it; then
    # two do, from both ends at once. There is no carving to watch yet —
    # randomize() throws every wall at once, so there is no order to it;
    # that beat arrives with the generator.
    ends = Drawing(entry=entry, exit=exit, title="A-MAZE-ING",
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
