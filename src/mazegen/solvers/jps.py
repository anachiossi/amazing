"""Jump point search: run down a corridor, stop where there is a choice.

Chosen in ``docs/2026-09-04-ALGORITHM-CHOICES.md`` §4.3. Instead of
expanding cell by cell, keep going in a straight line until something
happens — a junction, a wall, the goal — and queue only that cell. A
maze is mostly corridor and a little junction, and most of what A*
expands is a cell with nothing to decide.

Measured against A* in the study: **241 expansions to 406 on a perfect
maze, 325 to 470 braided**. Two things behind those numbers are worth
knowing before quoting them:

* **it is expansions, not work.** The same runs scanned 807 cells
  against 852 — 5% fewer. The saving is in queue operations; the jump
  still reads every cell it passes. Measure wall-clock once both
  exist.
* **the saving is bigger on a perfect maze than in Pac-Man mode** (41%
  against 31%), because open space gives more turning options and
  jumps end sooner — the opposite of how JPS is usually sold.

**Our grid needs its own jump rule**, and this one is measured: stop
at every cell where a turn is possible. The published rule is written
for 8-connected open grids; this maze is 4-connected and walled, so
the diagonal cases do not arise and "forced neighbour" reduces to "a
passage leads off the line I am running along".

BFS is the ground truth here too: the test is that it returns a route
of the same length, on every maze, for every seed.

Not written yet. ``name`` stays empty until it is, which is what keeps
it out of the registry — see ``MazeSolver.__init_subclass__``.
"""

from ..solver import MazeSolver


class JPS(MazeSolver):
    """Jump point search. The jump rule is still to write."""

    # Set to "jps" once _step works, and not before: an empty name is
    # what keeps a half-written solver from being selectable.
    name = ""

    def _initstruct(self) -> None:
        """Set up A*'s structures; the jumping is what differs.

        To write:

        * a heap of jump points still to look at, ordered by ``g + h``,
          with the entry on it;
        * ``g`` and the parent of each jump point;
        * ``self._path`` empty, as in ``BFS._initstruct``.

        The route is rebuilt from jump points, which are not adjacent,
        so walking the parents back gives corners rather than steps:
        the straight runs between them have to be filled back in
        before the path is handed out, or the output file will claim
        jumps no one can make.
        """
        raise NotImplementedError(
            "jump point search is not written yet")

    def _step(self) -> int:
        """Advance by one jump point. 0 to carry on, 1 when done.

        To write:

        * take the cheapest jump point from the heap;
        * from it, run along each open side in turn, cell after cell,
          until the run reaches the exit, hits a wall, or arrives at a
          cell with a passage leading off the line — that cell is the
          next jump point;
        * queue the jump points found, and return 0;
        * on reaching the exit, walk the parents back, fill in the
          straight runs between them, and return 1;
        * return 1 with an empty path if the heap empties.
        """
        raise NotImplementedError(
            "jump point search is not written yet")
