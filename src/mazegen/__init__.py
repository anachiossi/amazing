"""Reusable maze generator."""

from .generator import MazeGenerator
from .maze import Direction, Maze

# Imported for the side effect: it is what registers the algorithms,
# so ``MazeGenerator.named`` answers to them. Last, because the
# modules in it import MazeGenerator from above.
from . import generators  # noqa: F401,E402  (registration, not use)

__all__ = ["Direction", "Maze", "MazeGenerator"]
