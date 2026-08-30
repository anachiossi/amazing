"""Maze generation."""

from .maze import Maze


class MazeGenerator:
    """Generates mazes. Public class of the package."""

    def __init__(self, width: int, height: int, perfect: bool = False,
                 seed: int | None = None) -> None:
        """Configure the generator; ``seed`` makes the result repeatable."""
        # TODO
        raise NotImplementedError

    def generate(self) -> Maze:
        """Generate and return a new maze."""
        # TODO: pick the generation algorithm
        # TODO: never leave a 3x3 open area
        # TODO: carve the "42" pattern, or report that it does not fit
        raise NotImplementedError
