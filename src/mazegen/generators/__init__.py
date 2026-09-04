"""One module per generation algorithm.

Importing this package is what puts the algorithms in the registry, so
``MazeGenerator.named`` can find them. Adding an algorithm is a module
here and a line below.
"""

from .kruskal import Kruskal

__all__ = ["Kruskal"]
