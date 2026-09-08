"""Recursive division: cut a room in two, and leave a gap in the wall.

Chosen in ``docs/2026-09-04-ALGORITHM-CHOICES.md`` §2.3 as the third
paradigm — splitting space, where the other two carve a path and join
regions. Divide and conquer: cut the rectangle with a wall, punch a
gap in it, recurse into both halves.

Three things make it unlike the other two:

* it **starts from an open grid and puts walls up**, so it is the only
  caller of ``build_wall`` in the package;
* its recursion depth is ~log2 of the size rather than the number of
  cells, so it can stay recursive without risking Python's limit;
* it needs **no braiding pass**: two gaps in a wall instead of one is
  a loop, made as the wall goes up.

Not written yet. ``name`` stays empty until it is, which is what keeps
it out of the registry — see ``MazeGenerator.__init_subclass__``. A
config file asking for it meanwhile is refused with a message naming
the algorithms that do exist, which is what an unfinished algorithm
should do rather than half-run.
"""

from collections.abc import Iterator

from ..generator import MazeGenerator
from ..maze import Maze


class Division(MazeGenerator):
    """Recursive division. The algorithm itself is still to write."""

    # Set to "division" once _run works, and not before: an empty name
    # is what keeps a half-written algorithm from being selectable.
    name = ""

    def _blank(self) -> Maze:
        """An open room: every internal wall already down.

        The other two generators are handed a full grid and knock
        walls down. This one is handed an empty room and puts them up,
        which is why it overrides the default.
        """
        maze = Maze(self.config.width, self.config.height)
        for (col, row), side in maze.internal_walls():
            maze.destroy_wall(col, row, side)
        return maze

    def _run(self) -> Iterator[Maze]:
        """Split the maze, and keep splitting the halves.

        To write:

        * pick a wall line across the rectangle, and a gap in it;
        * build the wall, leaving the gap open — and a second gap when
          ``self.config.perfect`` is False, which is where the loops
          come from;
        * stop when a rectangle is too narrow to be cut in two;
        * recurse on the two halves;
        * yield ``self.maze`` after each wall, for the animation;
        * leave the "42" alone: ``self._touches_42(cell, side)`` says
          whether a wall belongs to it, and those cells are already
          closed before this runs.
        """
        raise NotImplementedError(
            "recursive division is not written yet")

    def _braid(self) -> Iterator[Maze]:
        """Nothing to do: the loops were made as the walls went up.

        The base class opens a wall at every dead-end to make loops.
        This generator makes them itself, by punching a second gap in
        each wall, so braiding afterwards would only thin the maze.
        """
        return iter([])
