"""Configuration file reading."""

from typing import Any, cast


class MazeConfigError(Exception):
    """Error raised when the config file or keys are invalid."""


class MazeConfig:
    """Values read from a ``KEY=VALUE`` file (ignores comments `#´)."""

    mandatory_keys: dict[str, type] = {
        "width": int,
        "height": int,
        "entry": tuple,
        "exit": tuple,
        "output_file": str,
        "perfect": bool,
    }

    # Keys for the mazegen that are optional.
    # If present, they will be converted.
    optional_keys: dict[str, type] = {
        "seed": int,
        "algorithm": str,
    }

    keys_limits: dict[str, tuple[int, int]] = {
        "width": (1, 1000),
        "height": (1, 1000),
    }

    def __init__(self, path: str) -> None:
        """Open the file, read its values, then check and convert them."""
        self._config: dict[str, Any] = {}
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
                    self._config[key.strip().lower()] = value.strip()
        except FileNotFoundError as error:
            raise MazeConfigError(f"config file not found: {path}") from error
        except OSError as error:
            raise MazeConfigError(f"cannot read {path}: {error}") from error

        self._check_mandatory_keys()
        self._values_casting()
        self._check_values()

    def _check_mandatory_keys(self) -> None:
        """Check that every mandatory key is present."""
        for key in self.mandatory_keys:
            if key not in self._config:
                raise MazeConfigError(f"missing mandatory key: {key.upper()}")

    def _values_casting(self) -> None:
        """Convert every known value to the type it must have."""
        to_convert = dict(self.mandatory_keys)
        for key, expected_type in self.optional_keys.items():
            if key in self._config:
                to_convert[key] = expected_type
        for key, expected_type in to_convert.items():
            value = self._config[key]
            if expected_type is int:
                self._config[key] = self._to_int(key, value)
            elif expected_type is bool:
                self._config[key] = self._to_bool(key, value)
            elif expected_type is tuple:
                self._config[key] = self._to_point(key, value)
            elif expected_type is str:
                pass  # already a string, nothing to convert
            else:
                raise MazeConfigError(
                    f"no conversion defined for {key.upper()} "
                    f"({expected_type.__name__})"
                )

    @staticmethod
    def _to_int(key: str, value: str) -> int:
        """Read a whole number, or say which key was wrong."""
        try:
            return int(value)
        except ValueError as error:
            raise MazeConfigError(
                f"{key.upper()} must be a whole number, got {value!r}"
            ) from error

    @staticmethod
    def _to_bool(key: str, value: str) -> bool:
        """Read a boolean. An unrecognised word is an error, not False."""
        lowered = value.lower()
        if lowered in ("true", "1", "yes"):
            return True
        if lowered in ("false", "0", "no"):
            return False
        raise MazeConfigError(
            f"{key.upper()} must be True or False, got {value!r}"
        )

    @staticmethod
    def _to_point(key: str, value: str) -> tuple[int, int]:
        """Read an ``y, x`` pair and keep it's order exactly as written.
        19,14 stays (19, 14): 20th column, 15th row."""
        parts = value.split(",")
        if len(parts) != 2:
            raise MazeConfigError(
                f"{key.upper()} must be written as y,x, got {value!r}"
            )
        try:
            col, row = (int(part.strip()) for part in parts)
        except ValueError as error:
            raise MazeConfigError(
                f"{key.upper()} must be two whole numbers, got {value!r}"
            ) from error
        return col, row

    def _check_values(self) -> None:
        """Check the values describe a maze that can exist."""
        for key, (lowest, highest) in self.keys_limits.items():
            size = cast(int, self._config[key])
            if not lowest <= size <= highest:
                raise MazeConfigError(
                    f"{key.upper()} must be between {lowest} and "
                    f"{highest}, got {size}"
                )
        width = cast(int, self._config["width"])
        height = cast(int, self._config["height"])
        for key in ("entry", "exit"):
            col, row = cast(tuple[int, int], self._config[key])
            if not (0 <= col < width and 0 <= row < height):
                raise MazeConfigError(
                    f"{key.upper()} falls outside a {width}x{height} maze: "
                    f"column {col}, row {row}"
                )
        if self._config["entry"] == self._config["exit"]:
            raise MazeConfigError("ENTRY and EXIT must be different cells")

    # The casts below are safe: _values_casting has already converted
    # every value, or raised before we got here.

    @property
    def width(self) -> int:
        return cast(int, self._config["width"])

    @property
    def height(self) -> int:
        return cast(int, self._config["height"])

    @property
    def entry(self) -> tuple[int, int]:
        return cast(tuple[int, int], self._config["entry"])

    @property
    def exit(self) -> tuple[int, int]:
        return cast(tuple[int, int], self._config["exit"])

    @property
    def output_file(self) -> str:
        return cast(str, self._config["output_file"])

    @property
    def is_perfect(self) -> bool:
        return cast(bool, self._config["perfect"])

    @property
    def seed(self) -> int | None:
        """Seed for reproducible generation, None if the file omits it."""
        return cast(int | None, self._config.get("seed"))

    @property
    def algorithm(self) -> str | None:
        """Requested generation algorithm, None if the file omits it."""
        return cast(str | None, self._config.get("algorithm"))

    def show_config(self) -> None:
        print("Maze configuration:")
        for key, value in self._config.items():
            print(f"{key} = {value}")
