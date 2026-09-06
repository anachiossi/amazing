
Cell = tuple[int, int]


class MazeSolverConfig:

    def __init__(self, width: int, height: int,
                 entry_cell: Cell, exit_cell: Cell,
                 perfect: bool = False, seed: int | None = None,
                 algorithm: str | None = None) -> None:
        if width < 1 or height < 1:
            raise ValueError(
                f"a maze needs at least one cell, got {width}x{height}"
            )
        for label, cell in (("entry", entry_cell), ("exit", exit_cell)):
            col, row = cell
            if not (0 <= col < width and 0 <= row < height):
                raise ValueError(
                    f"{label} {cell} falls outside a {width}x{height} maze"
                )
        self.width = width
        self.height = height
        self.entry_cell = entry_cell
        self.exit_cell = exit_cell
        self.perfect = perfect
        self.seed = seed
        self.algorithm = algorithm
