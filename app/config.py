"""Configuration file reading."""


class MazeConfig:
    """Values read from a ``KEY=VALUE`` file (``#`` starts a comment).

    Example:
        >>> config = MazeConfig("./config.txt")
        >>> config.width
        20
    """

    def __init__(self, path: str) -> None:
        """Open the file and read its values."""
        # TODO: parse KEY=VALUE using a context manager
        # TODO: check that every mandatory key is present
        # TODO: convert ENTRY/EXIT from "x,y" to (row, col)
        raise NotImplementedError

    @property
    def width(self) -> int:
        """Maze width in cells."""
        # TODO
        raise NotImplementedError

    @property
    def height(self) -> int:
        """Maze height in cells."""
        # TODO
        raise NotImplementedError

    @property
    def entry(self) -> tuple[int, int]:
        """Entry cell, as ``(row, col)``."""
        # TODO
        raise NotImplementedError

    @property
    def exit(self) -> tuple[int, int]:
        """Exit cell, as ``(row, col)``."""
        # TODO
        raise NotImplementedError

    @property
    def output_file(self) -> str:
        """Path of the output file."""
        # TODO
        raise NotImplementedError

    @property
    def perfect(self) -> bool:
        """True if the maze must be perfect."""
        # TODO
        raise NotImplementedError
