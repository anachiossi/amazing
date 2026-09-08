"""Bidirectional A*: aim with a heuristic, from both ends at once.

Chosen in ``docs/2026-09-04-ALGORITHM-CHOICES.md`` §4.2. Two ideas in
one algorithm: steer the search with a heuristic instead of spreading
evenly, and run two searches — one from the entry, one from the exit —
until they meet.

The **Manhattan distance is admissible** on this grid: every step
changes it by exactly one, so it never overestimates, and that is
precisely why the answer stays a shortest path. Two frontiers halve
the depth each search reaches, and the area explored grows with the
square of the depth, so meeting in the middle scans far less than one
search going the whole way — the fewest cells of anything measured in
the study.

**The one real trap**, worth reading before writing the stopping rule:
stopping the moment the two frontiers touch does *not* guarantee a
shortest path, because the first meeting can be through a cell neither
side has settled cheaply yet. The study's visualizer checks mid-level,
which the textbook says is unsafe, and over 600 test mazes — perfect
and braided — it never returned a longer path than BFS. Real in
theory, not reproduced here.

Which is what makes the test easy: BFS is the ground truth, so the
check is one line — *the same length as BFS, on every maze, for every
seed*. A pathfinder that is quietly wrong writes a wrong path into the
output file, where the analyzer finds it at the defence.

Not written yet. ``name`` stays empty until it is, which is what keeps
it out of the registry — see ``MazeSolver.__init_subclass__``.
"""

from ..solver import MazeSolver


class BidirectionalAStar(MazeSolver):
    """Bidirectional A*. The search itself is still to write."""

    # Set to "astar" once _step works, and not before: an empty name
    # is what keeps a half-written solver from being selectable.
    name = ""

    def _initstruct(self) -> None:
        """Set up the two searches, one from each end.

        To write, per side — so two of each:

        * a heap of cells still to look at, ordered by ``g + h``;
        * ``g``, the cost to reach each cell so far;
        * the parent of each cell, to walk the route back out;
        * the cells already settled.

        ``self._path`` starts empty, as in ``BFS._initstruct``.
        """
        raise NotImplementedError(
            "bidirectional A* is not written yet")

    def _step(self) -> int:
        """Advance one search by one cell. 0 to carry on, 1 when done.

        To write:

        * take the cheapest cell from whichever side is behind;
        * settle it, and relax its open neighbours —
          ``self.maze.passages(col, row)`` gives the ones with a way
          through;
        * when a cell has been settled by both sides, join the two
          halves into ``self._path``, entry first, and return 1;
        * return 1 with an empty path if either heap empties, which
          means the exit cannot be reached.
        """
        raise NotImplementedError(
            "bidirectional A* is not written yet")
