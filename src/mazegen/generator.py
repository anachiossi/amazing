"""Maze generation: the skeleton every algorithm shares.

``MazeGenerator`` runs the same five steps whatever the algorithm —
blank grid, "42", the algorithm itself, then the two passes that make a
maze playable. A subclass fills in ``_run`` and nothing else, unless it
builds the maze the other way round, in which case it also says so by
overriding ``_blank`` and ``_braid``.
"""

import random
from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Iterator

from .maze import Direction, Maze

Cell = tuple[int, int]
# A passage between two cells, held as the pair it joins so that it
# reads the same from either side.
Edge = frozenset[Cell]


class MazeGenerator(ABC):
    """Generates mazes. Public class of the package.

    The work is written as a generator: ``carve`` yields the maze after
    every change, and ``generate`` is that drained to the end. One
    implementation, so an animation and a finished maze cannot drift
    apart.

    The maze yielded is the live one, changed in place — it is the
    current state, not a snapshot, and the one before it no longer
    exists. Drawing each state as it arrives works; collecting them in
    a list gives the same maze many times.

    Subclasses fill in:

    ``_run``     the algorithm; the only thing that must be written
    ``_blank``   the grid it starts from, closed unless said otherwise
    ``_braid``   what ``PERFECT=False`` does, unless done while running
    """

    # Size of the "42" pattern itself, in cells.
    min_42: tuple[int, int] = (7, 5)
    max_42: tuple[int, int] = (13, 9)
    # Smallest maze that can hold it: the pattern plus one cell of margin
    # all around, without which the board splits into separate regions.
    min_maze_with_42: tuple[int, int] = (9, 7)

    # Every subclass that names itself is selectable by that name, so
    # adding an algorithm is writing a class and nothing else.
    algorithms: dict[str, type["MazeGenerator"]] = {}
    name: str = ""
    # Kruskal's while it is the only one written; the backtracker takes
    # this back when it lands, being the one that animates best.
    default: str = "kruskal"

    # The maze being built. It exists only while ``carve`` runs, so it
    # is declared rather than assigned: there is no maze before then.
    maze: Maze

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Record a named subclass so ``named`` can find it."""
        super().__init_subclass__(**kwargs)
        if cls.name:
            MazeGenerator.algorithms[cls.name] = cls

    def __init__(self,
                 width: int,
                 height: int,
                 entry: tuple[int, int],
                 exit: tuple[int, int],
                 perfect: bool = False,
                 seed: int | None = None) -> None:
        """Configure the generator; ``seed`` makes the result repeatable."""
        if width < 1 or height < 1:
            raise ValueError(
                f"a maze needs at least one cell, got {width}x{height}"
            )
        for label, cell in (("entry", entry), ("exit", exit)):
            col, row = cell
            if not (0 <= col < width and 0 <= row < height):
                raise ValueError(
                    f"{label} {cell} falls outside a {width}x{height} maze"
                )
        self.width = width
        self.height = height
        self.entry = entry
        self.exit = exit
        self.perfect = perfect
        self.seed = seed
        # Cells the "42" has sealed; no algorithm may open into them.
        self.sealed: frozenset[Cell] = frozenset()

    @classmethod
    def named(cls, algorithm: str | None = None,
              **settings: object) -> "MazeGenerator":
        """Return the generator that name asks for, configured.

        ``ALGORITHM`` in the config file is optional, so ``None`` is
        not a mistake and means the default. A name nobody answers to
        is a mistake, and says which names there are.
        """
        chosen = (algorithm or cls.default).strip().lower()
        if chosen not in cls.algorithms:
            known = ", ".join(sorted(cls.algorithms)) or "none registered"
            raise ValueError(
                f"no generation algorithm called {algorithm!r}; "
                f"there is {known}"
            )
        return cls.algorithms[chosen](**settings)  # type: ignore[arg-type]

    # -----------------------------------------------------------------
    # Running it

    def generate(self) -> Maze:
        """Generate and return a new maze."""
        for _ in self.carve():
            pass
        return self.maze

    def carve(self) -> Iterator[Maze]:
        """Yield the maze after each change, from blank to finished.

        This is what an animation consumes. ``generate`` is the same
        run with the states thrown away.
        """
        if self.seed is not None:
            random.seed(self.seed)
        self.maze = self._blank()
        yield self.maze
        yield from self._stamp_42()
        yield from self._run()
        if not self.perfect:
            yield from self._braid()
            yield from self._loosen()
        self.maze.set_entry(self.entry)
        self.maze.set_exit(self.exit)
        yield self.maze

    # -----------------------------------------------------------------
    # What a subclass fills in

    @abstractmethod
    def _run(self) -> Iterator[Maze]:
        """The algorithm itself, yielding after each wall it changes."""

    def _blank(self) -> Maze:
        """The grid the algorithm starts from: every wall standing.

        Recursive division overrides this — it adds walls rather than
        removing them, so it needs the opposite starting point.
        """
        return Maze(self.width, self.height)

    def _stamp_42(self) -> Iterator[Maze]:
        """Seal the "42" cells, before the algorithm runs.

        Not wired up yet: ``forty_two`` is still a stub. When it lands
        this records what it sealed in ``self.sealed``, so ``_is_free``
        keeps all three algorithms out of those cells rather than each
        of them having to remember.
        """
        return
        yield  # pragma: no cover - makes this a generator

    # -----------------------------------------------------------------
    # What PERFECT=False means, in two passes

    def _braid(self) -> Iterator[Maze]:
        """Open a wall at each dead-end, so the maze has loops.

        A dead-end is a cell you can only leave the way you came in.
        Opening one more of its walls joins it to a neighbour it was
        not joined to, and that is a loop.

        Local, one cell at a time: it never looks at the entry or the
        exit. That is why ``_loosen`` follows it.

        Recursive division overrides this to do nothing — it punches
        two gaps per wall as it runs, so the loops are already there.
        """
        for cell in self._dead_ends():
            shut = self._closed_walls(cell)
            if shut:
                self.maze.destroy_wall(*cell, random.choice(shut))
                yield self.maze

    def _loosen(self) -> Iterator[Maze]:
        """Open walls until no single one can cut the entry from the exit.

        ``_braid`` leaves no dead-ends, which is not the same as leaving
        two ways across: the loops it makes can all sit off to one side
        while every route still crosses one shared passage. Closing that
        passage would strand the exit, so there is only one route, and
        the config file promised two.

        A passage like that splits the maze in two when it is taken
        away. Any other wall standing between those two halves is a way
        round it, so opening one means the maze can no longer be cut in
        one place.

        Written the obvious way — every passage tried in turn — which is
        O(passages x search). The linear way is to look for bridges in
        one pass; this stays as the version that is plainly right.
        """
        while True:
            chokes = self._choke_points()
            if not chokes:
                return
            near = self._reachable(self.entry, banned=chokes[0])
            across = [(cell, side) for cell, side in self._closed_across(near)]
            if not across:
                return  # walled in by the "42" or the border: nothing to open
            cell, side = random.choice(across)
            self.maze.destroy_wall(*cell, side)
            yield self.maze

    # -----------------------------------------------------------------
    # Shared questions about the maze being built

    def _is_free(self, cell: Cell) -> bool:
        """Is that a cell of this maze the algorithm may touch?"""
        return cell in self.maze and cell not in self.sealed

    def _neighbours(self, cell: Cell) -> list[tuple[Cell, Direction]]:
        """The neighbours of that cell the algorithm may touch."""
        return [(other, side) for other, side in self.maze.neighbours(*cell)
                if self._is_free(other)]

    def _closed_walls(self, cell: Cell) -> list[Direction]:
        """The sides of that cell still walled, border and "42" apart."""
        return [side for other, side in self._neighbours(cell)
                if self.maze.get_wall(*cell, side)]

    def _dead_ends(self) -> list[Cell]:
        """Cells with one way in and out: three walls standing."""
        return [(col, row)
                for col in range(self.width)
                for row in range(self.height)
                if self._is_free((col, row))
                and self.maze.wall_count(col, row) == 3]

    def _reachable(self, start: Cell,
                   banned: Edge | None = None) -> set[Cell]:
        """Every cell reachable from that one, one passage barred.

        With nothing barred this is ``Maze.region_of``; the barred
        passage is what tells a choke point from an ordinary one.
        """
        if banned is None:
            return set(self.maze.region_of(*start))
        seen = {start}
        queue = deque([start])
        while queue:
            cell = queue.popleft()
            for other, _side in self.maze.passages(*cell):
                if frozenset((cell, other)) != banned and other not in seen:
                    seen.add(other)
                    queue.append(other)
        return seen

    def _open_edges(self) -> set[Edge]:
        """Every passage in the maze, each counted once."""
        return {frozenset(((col, row), other))
                for (col, row), side in self.maze.internal_walls()
                if not self.maze.get_wall(col, row, side)
                for other in (self._step(col, row, side),)}

    @staticmethod
    def _step(col: int, row: int, side: Direction) -> Cell:
        """The cell that side leads to."""
        step_col, step_row = side.step()
        return col + step_col, row + step_row

    def _choke_points(self) -> list[Edge]:
        """Passages every route from entry to exit has to use."""
        return [edge for edge in self._open_edges()
                if self.exit not in self._reachable(self.entry, banned=edge)]

    def _closed_across(self, near: set[Cell]) -> list[tuple[Cell, Direction]]:
        """Walls standing between the cells in ``near`` and the rest."""
        return [(cell, side)
                for col in range(self.width)
                for row in range(self.height)
                for cell in ((col, row),)
                for other, side in self._neighbours(cell)
                if self.maze.get_wall(*cell, side)
                and (cell in near) != (other in near)]

    # -----------------------------------------------------------------
    # The "42"

    def forty_two(self, maze: Maze) -> bool:
        """Draw the "42" pattern in the maze, if it fits.

        The pattern is drawn with fully closed cells, so every cell it
        covers gets all four of its walls built.

        Return True if it was drawn, False if it did not fit.
        """
        # TODO
        raise NotImplementedError

    def is_3x3_open(self, maze: Maze, col: int, row: int) -> bool:
        """Tell whether the 3x3 square centred on (col, row) is open.

        The central cell is 0000 and the neighbours have no walls between
        them; the walls on the outer side of the square may be present.
        """
        # TODO
        raise NotImplementedError
