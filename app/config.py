"""Configuration file reading."""

from mazegen import Cell, MazeGenerationConfig, MazeSolverConfig

# The maze sizes the program agrees to draw. The subject sets no
# ceiling; this one is here so that a slip like WIDTH=99999 is refused
# at once rather than after a very long wait.
MIN_SIZE = 1
MAX_SIZE = 1000

TRUE_WORDS = ("true", "1", "yes")
FALSE_WORDS = ("false", "0", "no")


class MazeConfigError(Exception):
    """Error raised when the config file or keys are invalid."""


class MazeConfig:
    """Values read from a ``KEY=VALUE`` file (ignores comments `#´).

    Each value is read and converted once, here, into an attribute of
    the type it has to have. Past ``__init__`` this object no longer
    speaks in strings, so nothing downstream has anything to convert
    or to check.
    """

    def __init__(self, path: str) -> None:
        """Open the file, read its values, then check and convert them."""
        values = _read(path)

        self.width: int = _int(values, "width")
        self.height: int = _int(values, "height")
        self.entry: Cell = _point(values, "entry")
        self.exit: Cell = _point(values, "exit")
        self.output_file: str = _need(values, "output_file")
        self.is_perfect: bool = _bool(values, "perfect")

        # Optional: absent is not an error, it means "you choose".
        self.seed: int | None = (
            _int(values, "seed") if "seed" in values else None
        )
        self.gen_algorithm: str | None = values.get("gen_algorithm")
        self.solve_algorithm: str | None = values.get("solve_algorithm")

        self._check()

    def _check(self) -> None:
        """Check the values describe a maze that can exist."""
        for name, size in (("WIDTH", self.width), ("HEIGHT", self.height)):
            if not MIN_SIZE <= size <= MAX_SIZE:
                raise MazeConfigError(
                    f"{name} must be between {MIN_SIZE} and "
                    f"{MAX_SIZE}, got {size}"
                )
        for name, (col, row) in (("ENTRY", self.entry), ("EXIT", self.exit)):
            if not (0 <= col < self.width and 0 <= row < self.height):
                raise MazeConfigError(
                    f"{name} falls outside a {self.width}x{self.height} "
                    f"maze: column {col}, row {row}"
                )
        if self.entry == self.exit:
            raise MazeConfigError("ENTRY and EXIT must be different cells")

    def to_generation_config(self) -> MazeGenerationConfig:
        """The same values, as mazegen's settings object.

        OUTPUT_FILE stays here: generation does not write the file.
        """
        return MazeGenerationConfig(
            width=self.width,
            height=self.height,
            entry_cell=self.entry,
            exit_cell=self.exit,
            perfect=self.is_perfect,
            seed=self.seed,
            algorithm=self.gen_algorithm,
        )

    def to_solver_config(self) -> MazeSolverConfig:
        """The same values, as mazegen's settings object.

        OUTPUT_FILE stays here: solving does not write the file.
        """
        return MazeSolverConfig(
            width=self.width,
            height=self.height,
            entry_cell=self.entry,
            exit_cell=self.exit,
            perfect=self.is_perfect,
            seed=self.seed,
            algorithm=self.solve_algorithm,
        )


def _read(path: str) -> dict[str, str]:
    """Every KEY=VALUE line of the file, keys lowered, values as written."""
    values: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as config_file:
            for number, raw in enumerate(config_file, start=1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    raise MazeConfigError(
                        f"{path}, line {number}: expected KEY=VALUE"
                    )
                key, value = line.split("=", 1)
                values[key.strip().lower()] = value.strip()
    except FileNotFoundError as error:
        raise MazeConfigError(f"config file not found: {path}") from error
    except OSError as error:
        raise MazeConfigError(f"cannot read {path}: {error}") from error
    return values


def _need(values: dict[str, str], key: str) -> str:
    """The value written for that key, or say which one is missing."""
    if key not in values:
        raise MazeConfigError(f"missing mandatory key: {key.upper()}")
    return values[key]


def _int(values: dict[str, str], key: str) -> int:
    """Read a whole number, or say which key was wrong."""
    value = _need(values, key)
    try:
        return int(value)
    except ValueError as error:
        raise MazeConfigError(
            f"{key.upper()} must be a whole number, got {value!r}"
        ) from error


def _bool(values: dict[str, str], key: str) -> bool:
    """Read a boolean. An unrecognised word is an error, not False."""
    value = _need(values, key)
    if value.lower() in TRUE_WORDS:
        return True
    if value.lower() in FALSE_WORDS:
        return False
    raise MazeConfigError(
        f"{key.upper()} must be True or False, got {value!r}"
    )


def _point(values: dict[str, str], key: str) -> Cell:
    """Read a ``col,row`` pair and keep its order exactly as written.

    19,14 stays (19, 14): the 20th column, the 15th row.
    """
    value = _need(values, key)
    parts = value.split(",")
    if len(parts) != 2:
        raise MazeConfigError(
            f"{key.upper()} must be written as col,row, got {value!r}"
        )
    try:
        col, row = (int(part.strip()) for part in parts)
    except ValueError as error:
        raise MazeConfigError(
            f"{key.upper()} must be two whole numbers, got {value!r}"
        ) from error
    return col, row
