"""Maze data structure.

This file implements the Maze class, which holds a grid of cells and
the hexadecimal encoding of their walls, one digit per cell, the one
the subject imposes and Direction describes.

The Maze class implements the API required to build a
maze. Specifically given an existing maze it allows to build and
destroy walls at specific locations through the methods build_wall()
and destroy_wall(). The API guarantees that the maze is transformed in
a coherent way as required by the subject.

On top of this class it is possible to build the rest:

- the generation algorithm, which carves a maze by destroying walls
- the solver, which walks the maze looking for the shortest path
- the renderer, which read the maze to draw it
"""

from enum import IntFlag


class Direction(IntFlag):
    """Used to represent the side of a cell as well as a specific movement.

    The subject imposes a particular strategy in how walls are encoded.

    For each cell of the grid we have a number that goes from 0 to
    15. The lowest value, 0, means all walls are open, while the
    highest value, 15, means all walls are closed. Specifically each
    bit of the number represents a specific wall. If its value is 1,
    then it is closed, otherwise it is open.

    The specific mapping between bit value and wall position is
    described as follows, where bit positions are given starting from
    the LSB (Least significant bit):

    | bit index | wall direction |
    ------------------------------
    |         0 | North          |
    |         1 | East           |
    |         2 | South          |
    |         3 | West           |

    A few examples to make this more clear:

    - If grid[col][row] = 0

      given that 0 in bit is 0000,
      then in position (col, row) all walls are open

    - If grid[col][row] = 15

      given that 15 in bit is 1111,
      then in position (col, row) all walls are closed

    - If grid[col][row] = 7

      given that 7 in bit is 0111,
      then in position (col, row) the North, East and South
      walls are closed and the West wall is open

    - If grid[col][row] = 9

      given that 9 in bit is 1001,
      then in position (col, row) the North and West walls are
      closed and the East and South walls are open

    """

    N = 0b0001  # 1
    E = 0b0010  # 2
    S = 0b0100  # 4
    W = 0b1000  # 8

    def opposite(self) -> "Direction":
        """Return the same wall, seen from the neighbouring cell.
        Supports a single side only.
        """
        return _OPPOSITE[self]

    def step(self) -> tuple[int, int]:
        """Return the (col, row) offset towards that neighbour.
        Supports a single side only.
        """
        return _STEP[self]


_OPPOSITE: dict[Direction, Direction] = {
    Direction.N: Direction.S,
    Direction.E: Direction.W,
    Direction.S: Direction.N,
    Direction.W: Direction.E,
}

_STEP: dict[Direction, tuple[int, int]] = {
    Direction.N: (0, -1),
    Direction.E: (1, 0),
    Direction.S: (0, 1),
    Direction.W: (-1, 0),
}

# To encode a cell with all walls we use the number 15, which is
# written in binary as 1111. We represent this value explicitly to
# avoid the usage of magic numbers.
ALL_WALLS = Direction.N | Direction.E | Direction.S | Direction.W


class Maze:
    """A grid of cells, each with 0 to 4 walls."""

    def __init__(self, width: int, height: int) -> None:
        """initialize each element of the grid with the value ALL_WALLS"""
        if width < 1 or height < 1:
            raise ValueError(
                f"a maze needs at least one cell, got {width}x{height}"
            )
        self.width = width
        self.height = height
        self.grid: list[list[Direction]] = []
        for _col in range(width):
            column: list[Direction] = []
            for _row in range(height):
                column.append(ALL_WALLS)
            self.grid.append(column)

    def get_dim(self) -> tuple[int, int]:
        return self.width, self.height

    def _is_inside(self, col: int, row: int) -> bool:
        """Tell whether the cell belongs to the grid."""
        return 0 <= col < self.width and 0 <= row < self.height

    def _check_bounds(self, col: int, row: int) -> None:
        """Refuse a cell that falls outside the grid."""
        if not self._is_inside(col, row):
            raise IndexError(
                f"cell ({col}, {row}) falls outside a "
                f"{self.width}x{self.height} maze"
            )

    def get_wall(self, col: int, row: int, direction: Direction) -> bool:
        """Tell whether the wall on that side is closed."""
        self._check_bounds(col, row)
        #
        # To extract the wall value we use the and-bit operation. If
        # the value is 1 it means wall is up, otherwise wall is
        # down. The cast to bool() is required because otherwise we
        # would obtain a Direction value such as, for example,
        # Direction.N, which is not stricly speaking a 0/1 value.
        #
        return bool(self.grid[col][row] & direction)

    def no_access(self, col: int, row: int) -> bool:
        """Check if a given cell position is closed by all four walls."""
        self._check_bounds(col, row)
        return self.grid[col][row] == ALL_WALLS

    def build_wall(self, col: int, row: int, direction: Direction) -> None:
        """Build a wall, updating the neighbouring cell as well.

        A wall belongs to two cells at once, so both sides are set and
        the grid never says one thing on one side and another on the
        other. On the border there is no neighbour and only the cell
        itself is touched.

        Notice that direction may hold several sides at once.
        For example build_wall(col, row, ALL_WALLS) will close a
        cell completely.
        """
        self._check_bounds(col, row)
        for side in Direction:
            if not side & direction:
                # We skip this side because it is not contained in
                # direction and we go directly to the next side.
                continue
            #
            # build the wall on the requested side
            #
            self.grid[col][row] |= side
            #
            # compute position of neighbour cell to update
            #
            step_col, step_row = side.step()
            neighbour_col, neighbour_row = col + step_col, row + step_row
            #
            # add the new wall to the neighbour cell only if it sits
            # within the grid, and add it to the opposite direction of
            # the starting wall.
            #
            if self._is_inside(neighbour_col, neighbour_row):
                self.grid[neighbour_col][neighbour_row] |= side.opposite()

    def destroy_wall(self, col: int, row: int, direction: Direction) -> None:
        """Destroy a wall, updating the neighbouring cell as well.

        A wall of the external border has no cell behind it and cannot
        be destroyed: the subject requires the border to stay
        closed. Asking for it is a mistake in the caller and so it is
        refused with an exception rather than ignored.

        Exactly as in build_wall(), direction may hold several sides
        at once.

        """
        self._check_bounds(col, row)
        #
        # the sides to open, each with the neighbour cell that shares
        # the wall with (col, row)
        #
        to_open: list[tuple[Direction, int, int]] = []
        for side in Direction:
            if not side & direction:
                # This side is not part of direction, skip to the next.
                continue
            step_col, step_row = side.step()
            neighbour_col, neighbour_row = col + step_col, row + step_row
            if not self._is_inside(neighbour_col, neighbour_row):
                raise ValueError(
                    f"the {side.name} wall of cell ({col}, {row}) is on "
                    f"the border of the maze and cannot be destroyed"
                )
            to_open.append((side, neighbour_col, neighbour_row))
        #
        # nothing can fail from here on
        #
        for side, neighbour_col, neighbour_row in to_open:
            #
            # to actually remove the walls we use the NOT operator (~)
            #
            self.grid[col][row] &= ~side
            self.grid[neighbour_col][neighbour_row] &= ~side.opposite()

    def adjacent_points(self, col: int, row: int) -> list[tuple[int, int]]:
        """List the cells that are adjacent to the given (col, row)
        regardless if the walls are present or not.

        """
        self._check_bounds(col, row)
        points: list[tuple[int, int]] = []
        for side in Direction:
            step_col, step_row = side.step()
            neighbour_col, neighbour_row = col + step_col, row + step_row
            if self._is_inside(neighbour_col, neighbour_row):
                points.append((neighbour_col, neighbour_row))
        return points

    def neighbours_points(self, col: int, row: int) -> list[tuple[int, int]]:
        """List the cells that are adjacent to the given (col, row)
        and for which there is an open passage. Which means that here
        walls are taken into consideration.

        Notice that a cell of the border is never returned, since the
        walls of the external border are always closed. The grid is
        checked all the same, so that the method keeps returning cells
        that exist even if a border wall were opened by mistake.

        """
        self._check_bounds(col, row)
        points: list[tuple[int, int]] = []
        for side in Direction:
            if self.get_wall(col, row, side):
                #
                # A closed wall on this side: no passage to the cell
                # behind it, whether or not that cell exists, so we
                # skip it and do not consider it
                #
                continue
            step_col, step_row = side.step()
            neighbour_col, neighbour_row = col + step_col, row + step_row
            #
            # Technically not needed because of the invariant that
            # border cells are always closed, yet a good defensive
            # guard to have regardless
            #
            if self._is_inside(neighbour_col, neighbour_row):
                points.append((neighbour_col, neighbour_row))
        return points
