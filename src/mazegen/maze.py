"""Maze data structure.

Coordinates are ``(col, row)`` — column first, the same order the config
file uses. The grid is a list of columns, so ``grid[col][row]`` keeps the
index order identical to the coordinate order and nothing is ever
swapped. ``row`` grows downwards.
"""

from enum import IntFlag


class Direction(IntFlag):
    """A cell side; the value is the encoding bit (1 = closed)."""

    N = 1
    E = 2
    S = 4
    W = 8

    # TODO: opposite -> the same wall seen from the neighbouring cell
    # TODO: step -> the (col, row) offset towards that neighbour,
    # TODO: N = (0, -1), E = (1, 0), S = (0, 1), W = (-1, 0)


class Maze:
    """A grid of cells, each with 0 to 4 walls."""

    def __init__(self, width: int, height: int) -> None:
        """Build a width by height maze."""
        # TODO: initialise grid[col][row] — width columns of height cells
        raise NotImplementedError

    def get_dim(self) -> tuple[int, int]:
        """Return ``(width, height)``."""
        # TODO
        raise NotImplementedError

    def get_wall(self, col: int, row: int, direction: Direction) -> bool:
        """Tell whether the wall on that side is closed."""
        # TODO
        raise NotImplementedError

    def no_access(self, col: int, row: int) -> bool:
        """Tell whether the cell is closed by all four walls."""
        # TODO
        raise NotImplementedError

    def build_wall(self, col: int, row: int, direction: Direction) -> None:
        """Build a wall, updating the neighbouring cell as well."""
        # TODO
        raise NotImplementedError

    def destroy_wall(self, col: int, row: int, direction: Direction) -> None:
        """Destroy a wall, updating the neighbouring cell as well."""
        # TODO
        raise NotImplementedError

    def neighbours_points(self, col: int, row: int) -> list[tuple[int, int]]:
        """List the neighbours reachable through an open passage."""
        # TODO
        raise NotImplementedError
