"""The picture: every pixel is a filled rectangle.

Draw order (later covers earlier): floor, path, entry/exit, walls.
Coordinates match the maze: column → x, row → y, origin top-left.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Sequence

import rainbow
from mazegen import Direction, Maze, Path

from .font import FONT, FONT_SCALE, FONT_WIDTH, ascii_only

Colour = int

# MLX reads the top byte as opacity; 0 is invisible.
OPAQUE = 0xFF000000

# Chrome around the maze, in pixels.
MARGIN = 24
LINE = 20
HEAD = 2 * LINE
TAIL_LINES = 7
FOOT = LINE
TAIL = TAIL_LINES * LINE + FOOT

MAX_CELL = 40
MIN_CELL = 6


def colour(name: str | int) -> Colour:
    """A rainbow name (or palette index) as opaque 0xAARRGGBB."""
    rgb: tuple[int, int, int] = rainbow.rgb_of(rainbow.number(name))
    red, green, blue = rgb
    return OPAQUE | (red << 16) | (green << 8) | blue


@dataclass(frozen=True)
class Skin:
    """Colour of each part of the drawing."""

    background: Colour
    floor: Colour
    wall: Colour
    path: Colour
    entry: Colour
    exit: Colour
    forty_two: Colour
    title: Colour
    message: Colour


STANDARD_SKIN = Skin(
    background=colour("cinder"),
    floor=colour("onyx"),
    wall=colour("chambray"),
    path=colour("yellow"),
    entry=colour("peppermint"),
    exit=colour("madder"),
    forty_two=colour("robin"),
    title=colour("snow"),
    message=colour("stone"),
)


class TooSmall(Exception):
    """Raised when a maze cannot be drawn on the screen there is."""


@dataclass(frozen=True)
class Layout:
    """Where the maze lands in the window, in pixels.

    A cell is ``cell`` pixels square. A wall is ``wall`` pixels thick
    and centred on the cell's edge.
    """

    width: int
    height: int
    cell: int
    min_width: int = 0

    @property
    def wall(self) -> int:
        """Wall thickness: a share of the cell, at least 1."""
        return max(1, self.cell // 8)

    @property
    def window(self) -> tuple[int, int]:
        """Window size that holds this drawing."""
        return (max(self.width * self.cell + 2 * MARGIN, self.min_width),
                self.height * self.cell + HEAD + TAIL)

    def corner(self, col: int, row: int) -> tuple[int, int]:
        """Top-left pixel of that cell.

        The maze is centred when the window is wider than the grid.
        """
        left = (self.window[0] - self.width * self.cell) // 2
        return left + col * self.cell, HEAD + row * self.cell

    def centre(self, col: int, row: int) -> tuple[int, int]:
        """Middle pixel of that cell."""
        left, top = self.corner(col, row)
        half = self.cell // 2
        return left + half, top + half

    @classmethod
    def fit(cls, maze: Maze, screen: tuple[int, int],
            min_width: int = 0) -> "Layout":
        """Largest cell that fits, up to MAX_CELL. Refuses below MIN_CELL."""
        width, height = maze.get_dim()
        across, down = screen
        cell = min(MAX_CELL,
                   (across - 2 * MARGIN) // width,
                   (down - HEAD - TAIL) // height)
        if cell < MIN_CELL:
            raise TooSmall(
                f"a {width}x{height} maze needs a cell of at least "
                f"{MIN_CELL} pixels, and this screen leaves room for "
                f"{max(cell, 0)}. Generate a smaller maze, or draw this "
                f"one in the terminal."
            )
        return cls(width, height, cell, min_width)


class Canvas:
    """A MiniLibX pixel buffer, and the one way of drawing into it.

    ``mlx_get_data_addr`` hands over the raw bytes. A rectangle is one
    row of colour copied line by line. ``mlx_pixel_put`` is not used.
    """

    def __init__(self, mlx: Any, mlx_ptr: Any,
                 width: int, height: int) -> None:
        self.width, self.height = width, height
        self.image = mlx.mlx_new_image(mlx_ptr, width, height)
        pixels, bits, self.stride, endian = mlx.mlx_get_data_addr(self.image)
        self.pixels = pixels
        self.depth = bits // 8
        # MLX endian 0 is little-endian, the usual host order.
        self.order: Literal["big", "little"] = ("big" if endian
                                                else "little")

    def rect(self, x: int, y: int, width: int, height: int,
             colour: Colour) -> None:
        """Fill a rectangle. Pixels off the image are clipped away."""
        left, top = max(x, 0), max(y, 0)
        right, bottom = min(x + width, self.width), min(y + height,
                                                        self.height)
        if right <= left or bottom <= top:
            return
        row = colour.to_bytes(self.depth, self.order) * (right - left)
        for line in range(top, bottom):
            start = line * self.stride + left * self.depth
            self.pixels[start:start + len(row)] = row

    def fill(self, colour: Colour) -> None:
        """Paint the whole buffer one colour."""
        self.rect(0, 0, self.width, self.height, colour)


def write_line(canvas: Canvas, text: str, top: int, ink: Colour) -> None:
    """Paint one centred line, 5x7 glyphs scaled by FONT_SCALE."""
    line = ascii_only(text)
    if not line:
        return
    glyph_w = FONT_WIDTH * FONT_SCALE
    left = max(0, (canvas.width - len(line) * glyph_w) // 2)
    for index, letter in enumerate(line):
        rows = (FONT.get(letter)
                or FONT.get(letter.swapcase())
                or FONT["?"])
        ox = left + index * glyph_w
        for row, bits in enumerate(rows):
            for col in range(FONT_WIDTH):
                if bits & (1 << (FONT_WIDTH - 1 - col)):
                    canvas.rect(ox + col * FONT_SCALE,
                                top + row * FONT_SCALE,
                                FONT_SCALE, FONT_SCALE, ink)


@dataclass
class Scene:
    """A maze, the route through it, and the captions for this drawing."""

    maze: Maze
    path: Path = ()
    title: str = ""
    message: Sequence[str] = ()


def draw(canvas: Canvas, maze: Maze, layout: Layout, skin: Skin,
         path: Path = ()) -> None:
    """Draw a maze into the canvas, floor first and walls last."""
    canvas.fill(skin.background)
    _cells(canvas, maze, layout, skin)
    _path(canvas, layout, path, skin.path)
    _ends(canvas, maze, layout, skin)
    _walls(canvas, maze, layout, skin.wall)


def _cells(canvas: Canvas, maze: Maze, layout: Layout,
           skin: Skin) -> None:
    """Floor of every cell; frozen cells ("42") in their own colour."""
    width, height = maze.get_dim()
    reserved = maze.get_frozen()
    for col in range(width):
        for row in range(height):
            left, top = layout.corner(col, row)
            inside = (skin.forty_two if (col, row) in reserved
                      else skin.floor)
            canvas.rect(left, top, layout.cell, layout.cell, inside)


def _path(canvas: Canvas, layout: Layout, path: Path,
          colour: Colour) -> None:
    """The route as one trail: each cell, plus the opening into the next."""
    for col, row in path:
        left, top = layout.corner(col, row)
        canvas.rect(left, top, layout.cell, layout.cell, colour)
    for step, cell in enumerate(path[:-1]):
        following = path[step + 1]
        x, y = layout.centre(*cell)
        other_x, other_y = layout.centre(*following)
        thick = layout.cell
        half = thick // 2
        canvas.rect(min(x, other_x) - half, min(y, other_y) - half,
                    abs(other_x - x) + thick, abs(other_y - y) + thick,
                    colour)


def _ends(canvas: Canvas, maze: Maze, layout: Layout,
          skin: Skin) -> None:
    """Entry and exit as smaller squares inside their cells."""
    inset = max(1, layout.cell // 4)
    side = layout.cell - 2 * inset
    for cell, ink in ((maze.get_entry(), skin.entry),
                      (maze.get_exit(), skin.exit)):
        if cell is None:
            continue
        left, top = layout.corner(*cell)
        canvas.rect(left + inset, top + inset, side, side, ink)


def _walls(canvas: Canvas, maze: Maze, layout: Layout,
           colour: Colour) -> None:
    """Every standing wall. Shared walls are drawn twice, same colour."""
    width, height = maze.get_dim()
    for col in range(width):
        for row in range(height):
            for side in Direction:
                if maze.get_wall(col, row, side):
                    canvas.rect(*_wall_rect(layout, col, row, side), colour)


def _wall_rect(layout: Layout, col: int, row: int,
               side: Direction) -> tuple[int, int, int, int]:
    """x, y, width, height of one wall, centred on the cell edge."""
    left, top = layout.corner(col, row)
    cell, thick = layout.cell, layout.wall
    half = thick // 2
    if side is Direction.N:
        return left - half, top - half, cell + thick, thick
    if side is Direction.S:
        return left - half, top + cell - half, cell + thick, thick
    if side is Direction.W:
        return left - half, top - half, thick, cell + thick
    return left + cell - half, top - half, thick, cell + thick
