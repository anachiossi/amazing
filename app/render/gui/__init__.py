"""Maze in a MiniLibX window.

1. MiniLibX gives a window and a pixel buffer (``Display``).
2. Everything on screen is a filled rectangle (``Canvas.rect``).
3. Draw floor, then path, then entry/exit, then walls.
4. Copy the buffer onto the window.
5. MiniLibX runs the loop; keys and animation are callbacks.

``draw.py`` is the picture. ``window.py`` is MiniLibX and the keys.
``font.py`` is the 5x7 glyphs (painted as rectangles too).
"""

from .draw import (FOOT, HEAD, LINE, MARGIN, MAX_CELL, MIN_CELL, STANDARD_SKIN,
                   TAIL, TAIL_LINES, Canvas, Layout, Scene, Skin, TooSmall,
                   colour, draw, write_line)
from .font import FONT as _FONT_5X7, ascii_only
from .window import (DOWN, ESCAPE, FORTY_TWO_COLOURS, KEYS, LEFT, RIGHT, UP,
                     WALL_COLOURS, Display, MazeWindow, Playback, key_letter,
                     path_prefixes, show)

__all__ = [
    "Canvas", "Display", "Layout", "MazeWindow", "Playback", "Scene",
    "Skin",
    "STANDARD_SKIN", "TooSmall", "ascii_only", "colour", "draw",
    "key_letter", "path_prefixes", "show", "write_line", "KEYS",
    "WALL_COLOURS", "FORTY_TWO_COLOURS", "_FONT_5X7",
    "DOWN", "ESCAPE", "FOOT", "HEAD", "LEFT", "LINE", "MARGIN",
    "MAX_CELL", "MIN_CELL", "RIGHT", "TAIL", "TAIL_LINES", "UP",
]
