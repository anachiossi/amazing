"""One module per pathfinding algorithm.

Importing this package is what puts the solvers in the registry, so
``MazeSolver.from_config`` can find them. Adding one is a module here
and a line below.

Three are planned, as ``docs/2026-09-04-ALGORITHM-CHOICES.md`` sets
out. BFS is the one that writes the output file and the ground truth
the other two are checked against: same route length, on every maze,
for every seed. A module that is still a stub is imported all the same,
but its class leaves ``name`` empty, so the registry does not offer it.
"""

from .bfs import BFS
from .astar import BidirectionalAStar  # stub: not registered yet
from .jps import JPS  # stub: not registered yet

__all__ = ["BFS", "BidirectionalAStar", "JPS"]
