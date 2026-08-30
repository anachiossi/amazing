"""Maze generation."""

from .maze import Maze


class MazeGenerator:
    """Generates mazes. Public class of the package."""

    # Size of the "42" pattern itself, in cells.
    min_42: tuple[int, int] = (7, 5)
    max_42: tuple[int, int] = (13, 9)
    # Smallest maze that can hold it: the pattern plus one cell of margin
    # all around, without which the board splits into separate regions.
    min_maze_with_42: tuple[int, int] = (9, 7)

    def __init__(self,
                 width: int,
                 height: int,
                 entry: tuple[int, int],
                 exit: tuple[int, int],
                 perfect: bool = False,
                 seed: int | None = None) -> None:
        """Configure the generator; ``seed`` makes the result repeatable."""
        self.width = width
        self.height = height
        self.entry = entry
        self.exit = exit
        self.perfect = perfect
        self.seed = seed

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

    def generate(self) -> Maze:
        """Generate and return a new maze."""
        # TODO: pick the generation algorithm
        raise NotImplementedError
