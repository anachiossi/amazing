"""Shortest path between two cells."""
import random
from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Sequence, Any

from . import forty_two
from .solver_config import MazeSolverConfig
from .maze import Direction, Maze

Cell = tuple[int, int]
# A passage between two cells, held as the pair it joins so that it
# reads the same from either side.
Edge = frozenset[Cell]

class MazeSolver(ABC):
    
    algorithms: dict[str, type["MazeSolver"]] = {}    
    name: str = ""
    default: str = "bfs"
    maze: Maze
    _path: list[Cell] = []

    # -----------------------------------------------------------------
    # Constructors and class lifecycle

    def __init__(self, config: MazeSolverConfig) -> None:
        self.config = config

    def __init_subclass__(cls) -> None:
        if cls.name:
            MazeSolver.algorithms[cls.name] = cls        

    @classmethod
    def from_config(cls, config: MazeSolverConfig) -> "MazeSolver":
        chosen = config.algorithm if config.algorithm is not None else cls.default
        chosen = chosen.strip().lower()
        if chosen not in cls.algorithms:
            known = ", ".join(sorted(cls.algorithms)) or "none registered"
            raise ValueError(
                f"no solver algorithm called {config.algorithm!r}; "
                f"there is {known}"
            )
        return cls.algorithms[chosen](config)

    def solve(self, maze: Maze) -> Sequence[Cell]:
        self.maze = maze
        self._initstruct()
        while self._step() == 0:
            pass
        return self._path

    @abstractmethod
    def _initstruct(self) -> None:
        """Initialize the data structures needed for the algorithm."""

    @abstractmethod
    def _step(self) -> Any | Sequence[Cell]:
        """Perform one step of the algorithm, yielding the curent state."""
    