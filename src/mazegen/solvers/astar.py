"""Bidirectional A* aims with a heuristic, from both ends at once."""

from heapq import heappop, heappush
from typing import NamedTuple

from ..maze import Cell, Path
from ..solver import MazeSolver


def manhattan(a: Cell, b: Cell) -> int:
    """Steps between two cells on a grid assuming no walls.

    Used in A* as the h component of the computation

    f = g + h

    Basically it describes an estimate for the future cost of getting

    Walls only ever lengthen the real route, so this never creates an
    overestimation on the distance and keeps the answer a shortest
    path. Every step changes it by exactly one, so a cell settled once
    is settled for good.
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

# This is the approximation used to estimate distance. 
h = manhattan

class Side(NamedTuple):
    """All data structured required by each side of the search"""
    #
    # a min-heap is just a list that is handled by specific functions
    # such as heappop and heappush in order to have good performance
    # when extracting the min element. What is pushed is
    # (g + h, h, cell): the total estimate first, since that is what
    # the ordering is on, then h alone to break ties towards the goal.
    #
    open: list[tuple[int, int, Cell]]
    # Cost from this side's root, for the best route found so far.
    g: dict[Cell, int]
    # Cell -> the cell it was reached from. None marks the root.
    parent: dict[Cell, None | Cell]
    # Cells settled for good, and so never to be expanded again.
    closed: set[Cell]
    # Every cell settled, in order, for the visualizer.
    anim: list[Cell]
    # Where this side is headed: the *other* side's root.
    goal: Cell

class BidirectionalAStar(MazeSolver):
    """Bidirectional A*. The search itself is still to write."""

    name = "astar"

    @staticmethod
    def _new_side(root: Cell, goal: Cell) -> Side:
        """One side, seeded with its root.
        """
        start_h = h(root, goal)
        return Side(
            open=[(0 + start_h, start_h, root)],
            g={root: 0},
            parent={root: None},
            closed=set(),
            anim=[root],
            goal=goal,
        )

    def _initstruct(self) -> None:
        entry, exit_ = self.config.entry_cell, self.config.exit_cell

        self.fwd = self._new_side(entry, exit_)
        self.bwd = self._new_side(exit_, entry)

        # Best complete route found so far. None until the two
        # searches have met anywhere at all.
        self.mu: int | None = None
        self.meeting: Cell | None = None

        self._path = []

    def _step(self) -> int:
        if not self.fwd.open or not self.bwd.open:
            # Out of frontier. With a meeting already recorded that is
            # a finish and not a failure: a route was found, there was
            # simply nothing left to prove a shorter one against.
            meeting = self.meeting
            if meeting is not None:
                self._join(meeting)
                return 1
            print("Bidirectional A* search over, path does not exist")
            return 1

        if len(self.fwd.open) < len(self.bwd.open):
            side, other = self.fwd, self.bwd
        else:
            side, other = self.bwd, self.fwd

        found = self._advance(side, other)
        if found is not None:
            # Two measured halves, so a real length and not an estimate.
            # If it is better than what we had, update it
            through = side.g[found] + other.g[found]
            if self.mu is None or through < self.mu:
                self.mu = through
                self.meeting = found

        # Every entry left on a heap has an f no smaller than the top
        # of that heap, and f is a floor on any route through its
        # cell. So once mu sits under both floors, nothing either side
        # could still turn up can beat it.
        #
        # Tested on every call and not only when something met: the
        # floors rise with each expansion, so a mu recorded long ago
        # becomes unbeatable at some later and otherwise quiet step.
        meeting, mu = self.meeting, self.mu
        if meeting is not None and mu is not None:
            # _advance may have emptied a heap, and an empty one has
            # no top to read. Leave it: the check above catches it on
            # the next call, and joins through this same meeting.
            if self.fwd.open and self.bwd.open:
                bound = min(self.fwd.open[0][0], self.bwd.open[0][0])
                if mu <= bound:
                    self._join(meeting)
                    return 1

        return 0

    def _advance(self, side: Side, other: Side) -> Cell | None:
        """Settle one cell of ``side``. The meeting cell, or None.

        Knows nothing about stopping: that stays in ``_step``, in one
        piece, so the rule that is easy to get wrong is written once.
        """
        _f, _h, cell = heappop(side.open)
        if cell in side.closed:
            # The cell is already settled with its final cost, so
            # nothing to do.
            return None

        # At this point we know chepeast route from side entry to this cell
        side.closed.add(cell)
        side.anim.append(cell)

        col, row = cell
        # One step on from a cell whose cost is settled, so it is the
        # same number for every neighbour and is worked out once.
        through = side.g[cell] + 1
        # passages() gives back the cell and the wall it lies through,
        # and only the cell is the child here.
        for child, _wall in self.maze.passages(col, row):
            if child in side.closed:
                continue
            if child in side.g and through >= side.g[child]:
                continue
            # Either new, or reached more cheaply than before
            side.g[child] = through
            child_h = h(child, side.goal)
            side.parent[child] = cell
            heappush(side.open, (through + child_h, child_h, child))

        # Settled from both ends, so the two halves make a whole route
        # and _step has a real length to weigh against mu.
        return cell if cell in other.closed else None

    def _join(self, meeting: Cell) -> None:
        """Both halves into ``self._path``, entry first."""
        # The forward parents run from the meeting back to the entry,
        # which is the wrong way round, so turn it over. The entry is
        # the one cell of that side with no parent, and None is what
        # ends the walk, exactly as in BFS.
        half: list[Cell] = []
        cell: Cell | None = meeting
        while cell is not None:
            half.append(cell)
            cell = self.fwd.parent[cell]
        half.reverse()

        # The backward parents run from the meeting out to the exit,
        # which is already the direction wanted, so this half is the
        # one needing no reversing. Start past the meeting so it is
        # not in the path twice.
        cell = self.bwd.parent[meeting]
        while cell is not None:
            half.append(cell)
            cell = self.bwd.parent[cell]

        self._path = half
