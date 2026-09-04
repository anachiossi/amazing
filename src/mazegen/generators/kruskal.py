"""Randomised Kruskal's: join cells until they are all one maze."""

import random
from collections.abc import Iterator

from ..generator import Cell, MazeGenerator
from ..maze import Maze


class _Forest:
    """The groups of already-joined cells, one tree each.

    Kruskal's asks one question over and over: can these two cells
    already reach each other? Each group is held as a tree, and a cell
    answers with the root of its tree, so two cells are joined exactly
    when they answer the same.
    """

    def __init__(self) -> None:
        # Both are filled in as cells are first asked about, so a maze
        # of any size costs nothing until its cells come up.
        self._parent: dict[Cell, Cell] = {}
        self._size: dict[Cell, int] = {}

    def _root(self, cell: Cell) -> Cell:
        """The cell that stands for the group this one is in.

        Every cell passed on the way up is re-pointed straight at the
        root, so the trees stay shallow however many joins happen.
        """
        self._parent.setdefault(cell, cell)
        self._size.setdefault(cell, 1)
        root = cell
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[cell] != root:
            self._parent[cell], cell = root, self._parent[cell]
        return root

    def join(self, one: Cell, other: Cell) -> bool:
        """Join the two groups, and say whether they were apart.

        ``False`` means they could already reach each other. That is
        the whole test: joining them a second way would make a loop.
        """
        left, right = self._root(one), self._root(other)
        if left == right:
            return False
        # The smaller group hangs off the larger, which is what keeps
        # the trees from growing into a line.
        if self._size[left] < self._size[right]:
            left, right = right, left
        self._parent[right] = left
        self._size[left] += self._size[right]
        return True


class Kruskal(MazeGenerator):
    """Kruskal's algorithm, with the walls taken in a random order.

    Every wall in the maze is considered once, shuffled. A wall comes
    down when the two cells it stands between cannot yet reach each
    other; otherwise it stays, because taking it down would make a
    second route between cells that already had one.

    The result is a spanning tree — every cell reachable, exactly one
    route between any two — which is what ``PERFECT=True`` asks for.
    ``_braid`` puts the loops back when it does not.

    It works on the whole board at once rather than walking it, so the
    maze appears everywhere at the same time: scattered fragments that
    grow together. That is what tells it apart from the backtracker on
    screen, and it is the reason it needs ``_Forest`` — there is no
    path being walked to say what is joined to what.
    """

    name = "kruskal"

    def _run(self) -> Iterator[Maze]:
        """Take the walls in a random order, opening the ones that join."""
        joined = _Forest()
        # Interior walls only, and none that would open into the "42".
        walls = [(cell, side) for cell, side in self.maze.internal_walls()
                 if self._is_free(cell)
                 and self._is_free(self._step(*cell, side))]
        random.shuffle(walls)
        for cell, side in walls:
            if joined.join(cell, self._step(*cell, side)):
                self.maze.destroy_wall(*cell, side)
                yield self.maze
