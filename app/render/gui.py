"""Rendering in a window, with MiniLibX.

The maze is read the same way the terminal renderer reads it — asked
for its size, its walls, its ends and its frozen cells, never written
to — but pixels are kinder than characters, and everything drawn here
is a rectangle::

    canvas.rect(x, y, width, height, colour)

That one call draws all of it. A cell is a rectangle, a wall is a thin
rectangle lying along one of its edges, and the path is a yellow
rectangle that fills each cell it visits and the opening into the
next, so the route is one trail rather than a run of separate tiles.
Nothing has to be looked up: two rectangles that meet at a corner are
already joined, which is the whole of what the terminal needs its
sixteen junction pieces for.

Coordinates
-----------

MLX counts pixels from the top-left corner, x to the right and y
downwards — the same way the maze counts cells. So ``col`` becomes x
and ``row`` becomes y, with nothing to flip::

    left, top ─┐
               ▼
               ┌───────┬───────┐   cell (0, 0) is the square whose
               │ (0,0) │ (1,0) │   top-left corner is (left, top),
               ├───────┼───────┤   and it is `cell` pixels across
               │ (0,1) │ (1,1) │   and the same down
               └───────┴───────┘

What is drawn, and in what order
--------------------------------

Later rectangles cover earlier ones, so the order is the order things
have to be seen in: the floor, then the path over it, then the two
ends over the path, and the walls last of all, because a wall is the
one thing nothing may be drawn over.

Colour
------

A colour here is one number, ``0xAARRGGBB``, and ``colour()`` turns
one of ``rainbow``'s names into it — the same names the terminal
renderer paints with, so the two look like the same program. The
leading byte is how opaque the colour is, and MLX means it: at 0 the
colour is perfectly invisible, so everything drawn here is opaque.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, replace
from time import monotonic
from typing import Any, Callable, Literal, Sequence

import rainbow
from mazegen import Direction, Maze, Path

Colour = int

# The alpha every colour is drawn with. MLX reads the top byte of a
# colour as how solid it is, and a colour without one is a colour that
# cannot be seen at all.
OPAQUE = 0xFF000000

# Room kept around the maze, in pixels: a margin either side, a head
# above it for the title, and a tail below it for the messages and the
# keys. Head and tail hold text, so they are counted in lines of it,
# and the tail holds as many lines as ``TAIL_LINES`` says — a longer
# message loses its first lines rather than its last, so the keys are
# never the thing that falls off. Three lines of keys plus the three
# captions and a blank between them is seven. ``FOOT`` is empty space
# under the last of those lines, so the keys are not on the window's
# bottom edge.
MARGIN = 24
LINE = 20
HEAD = 2 * LINE
TAIL_LINES = 7
FOOT = LINE
TAIL = TAIL_LINES * LINE + FOOT

# How long one animation frame stays on screen. carve() yields after
# every wall, so this is also how fast the maze grows.
FRAME = 0.012

# How big a cell may be. The largest is a matter of taste; the
# smallest is not, since a cell has to hold a wall on each side and
# still leave floor to see between them.
MAX_CELL = 40
MIN_CELL = 6

# Captions are painted into the maze image, not with mlx_string_put.
# MiniLibX's Vulkan backend only queues 64 image blits per frame, then
# clears and draws the rest: each letter is a blit, so a title plus the
# keys already overflow and wipe the maze (and the path). A 5x7 glyph
# scaled by two is ten pixels wide, which is also how the window width
# is estimated.
FONT_WIDTH = 5
FONT_SCALE = 2
CHARACTER = FONT_WIDTH * FONT_SCALE

# What the desktop keeps for itself: panels, the bar a window is
# dragged by, and room to see one window is not the whole screen. Taken
# off before the maze is fitted, so a big maze gets a window that can
# still be moved.
DESKTOP = (120, 160)

# The event MiniLibX sends when the window's close button is pressed.
DESTROY_NOTIFY = 33

# The keysym of Escape. Arrow keys are the other non-printable ones
# this window answers; every other key is a printable one, and those
# are their own character code — see ``key_letter``.
ESCAPE = 65307
LEFT = 65361
UP = 65362
RIGHT = 65363
DOWN = 65364
# The keypad arrows send a different keysym; they mean the same thing.
KEYPAD_LEFT = 65430
KEYPAD_UP = 65431
KEYPAD_RIGHT = 65432
KEYPAD_DOWN = 65433

ARROWS = {
    LEFT: "left",
    UP: "up",
    RIGHT: "right",
    DOWN: "down",
    KEYPAD_LEFT: "left",
    KEYPAD_UP: "up",
    KEYPAD_RIGHT: "right",
    KEYPAD_DOWN: "down",
}


def colour(name: str | int) -> Colour:
    """The colour ``rainbow`` knows by that name, as MLX wants it.

    ``rainbow`` names colours for the terminal, which draws from a
    palette of 256; a window draws in full colour, so the name is
    resolved to its red, green and blue and packed, opaque, into the
    single number MLX takes.
    """
    rgb: tuple[int, int, int] = rainbow.rgb_of(rainbow.number(name))
    red, green, blue = rgb
    return OPAQUE | (red << 16) | (green << 8) | blue


def key_letter(keysym: int) -> str:
    """The character on the key, or empty if this keysym is not a key we use.

    MLX reports X keysyms. A printable key's keysym is the character
    it types, so one ``chr`` is enough. Escape is returned as itself
    so the caller does not have to special-case the number, and the
    arrows as ``left``, ``up``, ``right`` and ``down``.
    """
    if keysym == ESCAPE:
        return "\x1b"
    if keysym in ARROWS:
        return ARROWS[keysym]
    if 32 <= keysym <= 126:
        return chr(keysym).lower()
    return ""


@dataclass(frozen=True)
class Skin:
    """The colour of every part of the drawing.

    A new look is a new instance of this class. Two of them are
    changed while the program runs — the walls and the "42" — which is
    why the skin is a value that can be replaced rather than something
    a drawing edits in place.
    """

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

# What C and F cycle through, in the order they are offered. The first
# of each is what the standard skin already draws with, so the first
# press moves to something else.
WALL_COLOURS = ("chambray", "vermilion", "gamboge", "peppermint",
                "ultramarine")
FORTY_TWO_COLOURS = ("robin", "cadmium", "flamingo", "verdigris", "snow")

# The keys, as the window itself says them. The window owns these
# lines because it owns the keys: whoever opens it should not have to
# know what it answers to. The first line is how you live in the maze;
# the second is how you change it.
KEYS = (
    "R generate   P path   Q quit",
    "C wall colour   F 42 colour",
    "G gen. alg.   A gen. anim.   S solver alg.   V solver anim.",
)

# The window is never narrower than the longest line of keys: a key
# nobody can read is a key nobody has.
MIN_WINDOW_WIDTH = max(len(line) for line in KEYS) * CHARACTER + 2 * MARGIN


# What the font has instead of the characters a caption is likely to
# carry. The 5x7 glyphs are ASCII; everything past that is a "?".
PLAIN = {"·": "-", "—": "-", "×": "x", "’": "'", "“": '"', "”": '"'}


def ascii_only(text: str) -> str:
    """The same line, in characters the font can draw."""
    for fancy, plain in PLAIN.items():
        text = text.replace(fancy, plain)
    return "".join(letter if letter.isascii() else "?" for letter in text)


_FONT_5X7: dict[str, tuple[int, ...]] = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    "-": (0, 0, 14, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 4, 0),
    ":": (0, 4, 4, 0, 4, 4, 0),
    "0": (14, 17, 19, 21, 25, 17, 14),
    "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 6, 8, 16, 31),
    "3": (14, 17, 1, 6, 1, 17, 14),
    "4": (2, 6, 10, 18, 31, 2, 2),
    "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14),
    "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (31, 17, 2, 4, 8, 0, 8),
    "?": (14, 17, 1, 2, 4, 0, 4),
    "A": (14, 17, 17, 31, 17, 17, 17),
    "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14),
    "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 19, 17, 17, 14),
    "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14),
    "J": (1, 1, 1, 1, 17, 17, 14),
    "K": (17, 18, 20, 24, 20, 18, 17),
    "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (14, 17, 16, 14, 1, 17, 14),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 21, 10),
    "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4),
    "Z": (31, 1, 2, 4, 8, 16, 31),
    "a": (0, 0, 14, 1, 15, 17, 15),
    "b": (16, 16, 30, 17, 17, 17, 30),
    "c": (0, 0, 14, 17, 16, 17, 14),
    "d": (1, 1, 15, 17, 17, 17, 15),
    "e": (0, 0, 14, 17, 31, 16, 14),
    "f": (6, 8, 28, 8, 8, 8, 8),
    "g": (0, 0, 15, 17, 15, 1, 14),
    "h": (16, 16, 30, 17, 17, 17, 17),
    "i": (4, 0, 12, 4, 4, 4, 14),
    "j": (4, 0, 12, 4, 4, 20, 8),
    "k": (16, 16, 18, 20, 24, 20, 18),
    "l": (12, 4, 4, 4, 4, 4, 14),
    "m": (0, 0, 27, 21, 21, 21, 17),
    "n": (0, 0, 30, 17, 17, 17, 17),
    "o": (0, 0, 14, 17, 17, 17, 14),
    "p": (0, 0, 30, 17, 30, 16, 16),
    "q": (0, 0, 15, 17, 15, 1, 1),
    "r": (0, 0, 22, 25, 16, 16, 16),
    "s": (0, 0, 15, 16, 14, 1, 30),
    "t": (8, 8, 28, 8, 8, 8, 6),
    "u": (0, 0, 17, 17, 17, 17, 15),
    "v": (0, 0, 17, 17, 17, 10, 4),
    "w": (0, 0, 17, 17, 21, 21, 10),
    "x": (0, 0, 17, 10, 4, 10, 17),
    "y": (0, 0, 17, 17, 15, 1, 14),
    "z": (0, 0, 31, 2, 4, 8, 31),
}


def write_line(canvas: Canvas, text: str, top: int, ink: Colour) -> None:
    """Paint one centred line into the image, 5x7 glyphs scaled by two."""
    line = ascii_only(text)
    if not line:
        return
    glyph_w = FONT_WIDTH * FONT_SCALE
    left = max(0, (canvas.width - len(line) * glyph_w) // 2)
    for index, letter in enumerate(line):
        rows = _FONT_5X7.get(letter) or _FONT_5X7.get(letter.swapcase()) or _FONT_5X7["?"]
        ox = left + index * glyph_w
        for row, bits in enumerate(rows):
            for col in range(FONT_WIDTH):
                if bits & (1 << (FONT_WIDTH - 1 - col)):
                    canvas.rect(ox + col * FONT_SCALE,
                                top + row * FONT_SCALE,
                                FONT_SCALE, FONT_SCALE, ink)


class TooSmall(Exception):
    """Raised when a maze cannot be drawn on the screen there is."""


@dataclass(frozen=True)
class Layout:
    """Where the maze lands in the window, in pixels.

    A cell is a square of ``cell`` pixels. The wall on its edge is
    ``wall`` pixels thick and sits centred on that edge, so the two
    cells sharing it give half each and the grid stays square.
    """

    width: int
    height: int
    cell: int

    @property
    def wall(self) -> int:
        """How thick a wall is drawn: a share of the cell, at least 1."""
        return max(1, self.cell // 8)

    @property
    def window(self) -> tuple[int, int]:
        """How big a window has to be to hold this drawing."""
        return (max(self.width * self.cell + 2 * MARGIN, MIN_WINDOW_WIDTH),
                self.height * self.cell + HEAD + TAIL)

    def corner(self, col: int, row: int) -> tuple[int, int]:
        """The top-left pixel of that cell.

        Worked out from the window rather than from the margin, so a
        maze narrower than the line of keys sits in the middle of the
        window it was given instead of against its left edge.
        """
        left = (self.window[0] - self.width * self.cell) // 2
        return left + col * self.cell, HEAD + row * self.cell

    def centre(self, col: int, row: int) -> tuple[int, int]:
        """The middle pixel of that cell."""
        left, top = self.corner(col, row)
        half = self.cell // 2
        return left + half, top + half

    @classmethod
    def fit(cls, maze: Maze,
            screen: tuple[int, int]) -> "Layout":
        """The roomiest drawing of that maze that the screen can hold.

        The window is made to measure — as many pixels as the maze
        needs and no more — so what has to be decided is the one thing
        both of its sides depend on: how big a cell is. The biggest
        that fits both ways is taken, up to ``MAX_CELL``, below which a
        bigger cell is only a bigger window.

        A maze so large that even ``MIN_CELL`` will not fit gets a
        refusal rather than a drawing nobody could read.
        """
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
        return cls(width, height, cell)


class Canvas:
    """An MLX image, and the one way of drawing into it.

    MLX hands over the raw pixels of an image, so a rectangle is
    written straight into that memory: one row of it built once, then
    copied line by line. The alternative, ``mlx_pixel_put``, is a call
    into the C library for every single pixel — the same drawing, a
    thousand times the calls.
    """

    def __init__(self, mlx: Any, mlx_ptr: Any,
                 width: int, height: int) -> None:
        self.width, self.height = width, height
        self.image = mlx.mlx_new_image(mlx_ptr, width, height)
        pixels, bits, self.stride, endian = mlx.mlx_get_data_addr(self.image)
        self.pixels = pixels
        # A pixel is a whole number of bytes, written in the order the
        # server asks for: MLX says which with `endian`, 0 for the
        # little-endian one every ordinary machine uses.
        self.depth = bits // 8
        self.order: Literal["big", "little"] = ("big" if endian
                                                else "little")

    def rect(self, x: int, y: int, width: int, height: int,
             colour: Colour) -> None:
        """Fill a rectangle. Whatever falls off the image is cut away.

        Clipping here rather than at every call site is what lets a
        wall hang half its thickness past the edge of the maze, and
        what makes the drawing survive a rectangle that lands nowhere.
        """
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
        """Paint the whole image one colour."""
        self.rect(0, 0, self.width, self.height, colour)


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
    """The inside of every cell: floor, or the "42" in its own colour.

    The shape is asked for by name rather than read off the walls: a
    cell closed on all four sides is one that was set aside for the
    "42", and, in a maze still being carved, also one that nothing has
    reached yet.
    """
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
    """The route, as one yellow trail through the cells it visits.

    Each cell of the path is filled, and so is the opening into the
    next, so neighbouring cells join instead of sitting as separate
    tiles. Walls are drawn later and cover the edges they own. An
    empty route draws nothing at all.
    """
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
    """Entry and exit, each a square sitting inside its own cell.

    Drawn after the path, so the two ends stay visible once the route
    that runs through them is shown.
    """
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
    """Every wall that stands, drawn on the edge it belongs to.

    Each cell draws all four of its sides, so the wall between two
    cells is drawn twice. That costs a rectangle and saves the reader
    a rule about which of the two cells owns it — the same pixels
    painted the same colour twice cannot show.
    """
    width, height = maze.get_dim()
    for col in range(width):
        for row in range(height):
            for side in Direction:
                if maze.get_wall(col, row, side):
                    canvas.rect(*_wall_rect(layout, col, row, side), colour)


def _wall_rect(layout: Layout, col: int, row: int,
               side: Direction) -> tuple[int, int, int, int]:
    """The rectangle one wall covers: x, y, width and height.

    A wall lies centred on the edge of its cell and runs half its
    thickness past each end. That overhang is what fills the corner
    where two walls meet, and what the canvas clips away at the border
    of the maze.
    """
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


@dataclass
class Scene:
    """A maze, the way through it, and what to say about it.

    The four of them travel together because they change together: a
    new maze has a new route, and a caption naming how it was made is
    only true of that maze. So regenerating hands back one of these
    rather than three things the window would have to keep in step.
    """

    maze: Maze
    path: Path = ()
    title: str = ""
    message: Sequence[str] = ()


@dataclass
class Playback:
    """A maze that arrives one change at a time, then a finished scene.

    ``frames`` is what ``carve()`` yields. ``finish`` is called with the
    last maze once the iterator is spent, so the path can be solved
    against the finished grid rather than a half-carved one.
    """

    frames: Iterator[Maze]
    finish: Callable[[Maze], Scene]


def path_prefixes(path: Path) -> Iterator[Path]:
    """The route revealed one cell at a time, empty first."""
    for end in range(len(path) + 1):
        yield path[:end]


class MazeWindow:
    """A window showing one maze, and the keys that change it.

    MLX owns the loop once it is started, so it also owns when things
    are drawn: this class hands it a few callbacks and never draws of
    its own accord. ``draw`` is one of them, hooked to expose, which
    is what makes the drawing survive being covered up and uncovered.

    What the keys do to the maze itself is not this window's to
    decide. ``on_maze`` is the way out of that: whoever opens the
    window says what R, G, S and the arrows do, and the window asks.
    A and V only flip bits here; the next R or G reads them.
    """

    def __init__(self, scene: Scene, skin: Skin = STANDARD_SKIN,
                 on_maze: Callable[[str, bool], Scene | Playback | None]
                 | None = None) -> None:
        # Imported here rather than at the top of the file: MLX is
        # only needed by a program that opens a window, and the rest
        # of this module is drawing anyone can read and test without
        # the library installed.
        from mlx import Mlx

        self.mlx = Mlx()
        self.mlx_ptr = self.mlx.mlx_init()
        self.scene = scene
        self.skin = skin
        self.on_maze = on_maze
        self.show_path = False
        self.gen_anim = False
        self.solver_anim = False
        self.wall_colour = 0
        self.forty_two_colour = 0
        self._play: Playback | None = None
        self._path_play: Iterator[Path] | None = None
        self._due = 0.0

        _, across, down = self.mlx.mlx_get_screen_size(self.mlx_ptr)
        self.layout = Layout.fit(
            scene.maze, (across - DESKTOP[0], down - DESKTOP[1]))
        window_width, window_height = self.layout.window
        self.window = self.mlx.mlx_new_window(
            self.mlx_ptr, window_width, window_height, scene.title or "maze")
        self.canvas = Canvas(self.mlx, self.mlx_ptr,
                             window_width, window_height)

    def run(self) -> None:
        """Open the window, and hand the program over to MLX."""
        self.mlx.mlx_expose_hook(self.window, self.draw, 0)
        self.mlx.mlx_key_hook(self.window, self._on_key, 0)
        self.mlx.mlx_hook(self.window, DESTROY_NOTIFY, 0, self._on_close,
                          0)
        # Drawn once here as well: the window is on screen by now, and
        # whether its first expose event reaches the hook above is the
        # server's business rather than something to rely on.
        self.draw()
        # Extra KeyPress events while a key is held. Display-wide, so
        # it is turned back on when the loop ends.
        self.mlx.mlx_do_key_autorepeatoff(self.mlx_ptr)
        try:
            self.mlx.mlx_loop(self.mlx_ptr)
        finally:
            self.mlx.mlx_do_key_autorepeaton(self.mlx_ptr)
        self.mlx.mlx_destroy_image(self.mlx_ptr, self.canvas.image)
        self.mlx.mlx_destroy_window(self.mlx_ptr, self.window)
        self.mlx.mlx_release(self.mlx_ptr)

    def draw(self, _param: Any = None) -> None:
        """Draw everything: the maze and the text, then show the image."""
        draw(self.canvas, self.scene.maze, self.layout, self.skin,
             self.scene.path if self.show_path else ())
        # Text is pixels in the same image. mlx_string_put is one GPU
        # blit per letter; after 64 MiniLibX clears the frame and the
        # maze (and the path) vanish under leftover glyphs.
        keys = list(KEYS)
        keys[0] = keys[0].replace(
            "P path", "P hide path" if self.show_path else "P path")
        keys[-1] = keys[-1].replace(
            "A gen. anim.", "A gen. on" if self.gen_anim else "A gen. anim.")
        keys[-1] = keys[-1].replace(
            "V solver anim.",
            "V solver on" if self.solver_anim else "V solver anim.")
        write_line(self.canvas, self.scene.title, HEAD - LINE,
                   self.skin.title)
        bottom = self.layout.window[1] - TAIL
        lines = [*self.scene.message, "", *keys][-TAIL_LINES:]
        for number, text in enumerate(lines):
            write_line(self.canvas, text, bottom + (number + 1) * LINE,
                       self.skin.message)
        self.mlx.mlx_put_image_to_window(self.mlx_ptr, self.window,
                                         self.canvas.image, 0, 0)
        self.mlx.mlx_do_sync(self.mlx_ptr)

    def _on_key(self, keysym: int, _param: Any = None) -> None:
        """Answer one key. The patched MiniLibX sends one KeyPress per tap."""
        self._apply(key_letter(keysym))

    def _apply(self, key: str) -> None:
        """Carry out one tap. Called once per physical keystroke."""
        if key in ("\x1b", "q"):
            self.mlx.mlx_loop_exit(self.mlx_ptr)
            return
        if key == "a":
            self.gen_anim = not self.gen_anim
        elif key == "v":
            self.solver_anim = not self.solver_anim
        elif key == "p":
            if self.show_path:
                self.show_path = False
            elif self.solver_anim and self.scene.path:
                self._begin_path(self.scene.path)
                return
            else:
                self.show_path = True
        elif key == "c":
            self.wall_colour = (self.wall_colour + 1) % len(WALL_COLOURS)
            self.skin = replace(
                self.skin, wall=colour(WALL_COLOURS[self.wall_colour]))
        elif key == "f":
            self.forty_two_colour = ((self.forty_two_colour + 1)
                                     % len(FORTY_TWO_COLOURS))
            self.skin = replace(
                self.skin,
                forty_two=colour(FORTY_TWO_COLOURS[self.forty_two_colour]))
        elif self.on_maze is not None:
            if self._play is not None and key not in ("r", "g"):
                return
            result = self.on_maze(key, self.gen_anim)
            if result is None:
                return
            if isinstance(result, Playback):
                self._begin(result)
                return
            self._stop()
            self.scene = result
        else:
            return
        self.draw()

    def _on_close(self, _param: Any = None) -> None:
        """Leave when the window's close button is pressed."""
        self.mlx.mlx_loop_exit(self.mlx_ptr)

    def _begin(self, play: Playback) -> None:
        """Start carving on the loop hook, one wall per frame."""
        self._stop()
        self._play = play
        try:
            maze = next(play.frames)
        except StopIteration:
            self.scene = play.finish(self.scene.maze)
            self.draw()
            return
        self.scene.maze = maze
        self.scene.path = ()
        self.draw()
        self._due = monotonic() + FRAME
        self.mlx.mlx_loop_hook(self.mlx_ptr, self._tick, 0)

    def _begin_path(self, path: Path) -> None:
        """Reveal the solved route one cell at a time."""
        self._path_play = path_prefixes(path)
        self.show_path = True
        self._due = monotonic()
        self.mlx.mlx_loop_hook(self.mlx_ptr, self._tick, 0)
        self._tick()

    def _tick(self, _param: Any = None) -> None:
        """Advance the playing animation if a frame is due."""
        if monotonic() < self._due:
            return
        self._due = monotonic() + FRAME
        if self._play is not None:
            try:
                self.scene.maze = next(self._play.frames)
                self.scene.path = ()
                self.draw()
            except StopIteration:
                play = self._play
                self._play = None
                self.scene = play.finish(self.scene.maze)
                if self.solver_anim and self.scene.path:
                    self._begin_path(self.scene.path)
                else:
                    self._stop()
                    self.draw()
            return
        if self._path_play is not None:
            try:
                self.scene.path = next(self._path_play)
                self.draw()
            except StopIteration:
                self._path_play = None
                self._stop()

    def _stop(self) -> None:
        """Take the loop hook off when nothing is playing."""
        self._play = None
        self._path_play = None
        self.mlx.mlx_loop_hook(self.mlx_ptr, None, 0)


def show(scene: Scene, skin: Skin = STANDARD_SKIN,
         on_maze: Callable[[str, bool], Scene | Playback | None] | None = None
         ) -> None:
    """Open a window on that maze and run until the user leaves."""
    MazeWindow(scene, skin, on_maze).run()


__all__ = ["Canvas", "Layout", "MazeWindow", "Playback", "Scene", "Skin",
           "STANDARD_SKIN", "TooSmall", "ascii_only", "colour", "draw",
           "key_letter", "path_prefixes", "show", "write_line", "KEYS",
           "WALL_COLOURS", "FORTY_TWO_COLOURS"]
