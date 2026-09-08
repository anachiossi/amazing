"""One module per generation algorithm.

Importing this package is what puts the algorithms in the registry, so
``MazeGenerator.from_config`` can find them. Adding an algorithm is a module
here and a line below.

Three are planned, one per paradigm, as
``docs/2026-09-04-ALGORITHM-CHOICES.md`` sets out. A module that is
still a stub is imported all the same — it keeps the file honest under
the linters — but its class leaves ``name`` empty, so the registry does
not offer it and a config file naming it is refused.
"""

from .kruskal import Kruskal
from .backtracker import Backtracker
from .division import Division  # stub: not registered yet

__all__ = ["Kruskal", "Backtracker", "Division"]
