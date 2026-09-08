"""Rendering in a window, with MiniLibX.

The maze is read the same way the terminal renderer reads it — asked
for its size, its walls, its ends and its frozen cells, never written
to — but pixels are kinder than characters, and everything drawn here
is a rectangle::

    canvas.rect(x, y, width, height, colour)

That one call draws all of it. A cell is a rectangle, a wall is a thin
rectangle lying along one of its edges, and the path is a rectangle
running from the middle of one cell to the middle of the next. Nothing
has to be looked up: two rectangles that meet at a corner are already
joined, which is the whole of what the terminal needs its sixteen
junction pieces for.

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

from dataclasses import dataclass, replace
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
# never the thing that falls off.
MARGIN = 24
LINE = 20
HEAD = 2 * LINE
TAIL_LINES = 5
TAIL = TAIL_LINES * LINE

# How big a cell may be. The largest is a matter of taste; the
# smallest is not, since a cell has to hold a wall on each side and
# still leave floor to see between them.
MAX_CELL = 40
MIN_CELL = 6

# How wide a character of the font MLX writes with comes out. The font
# cannot be asked, so this is measured rather than read, and centring
# a line of text is an estimate — near enough for a title, and the
# reason nothing here is laid out against the text.
CHARACTER = 10

# What the desktop keeps for itself: panels, the bar a window is
# dragged by, and room to see one window is not the whole screen. Taken
# off before the maze is fitted, so a big maze gets a window that can
# still be moved.
DESKTOP = (120, 160)

# The X event a window's close button sends.
DESTROY_NOTIFY = 33

# The keysym of Escape. Every other key this window listens for is a
# printable one, and those are their own character code — see
# ``_on_key``.
ESCAPE = 65307


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
    path=colour("gamboge"),
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

# The keys, as the window itself says them. The window owns this line
# because it owns the keys: whoever opens it should not have to know
# what it answers to.
KEYS = "R new maze   P path   C wall colour   F 42 colour   Q quit"

# The window is never narrower than the line of keys: a key nobody can
# read is a key nobody has.
MIN_WINDOW_WIDTH = len(KEYS) * CHARACTER + 2 * MARGIN


# What the font has instead of the characters a caption is likely to
# carry. MLX writes with an X core font, which knows ASCII and nothing
# else: everything past it comes out as a pair of question marks.
PLAIN = {"·": "-", "—": "-", "×": "x", "’": "'", "“": '"', "”": '"'}


def ascii_only(text: str) -> str:
    """The same line, in characters the font can draw."""
    for fancy, plain in PLAIN.items():
        text = text.replace(fancy, plain)
    return "".join(letter if letter.isascii() else "?" for letter in text)


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
        """The middle pixel of that cell, where the path runs."""
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
    """The route, as one rectangle per step.

    A rectangle drawn from the middle of one cell to the middle of the
    next covers both middles and everything between them, so a route
    turns a corner without anyone drawing the corner.

    The last cell has no next one and is joined to itself, which comes
    out as the square at the middle that ends the line. A route of one
    cell is that square and nothing else, and an empty route draws
    nothing at all.
    """
    thick = max(2, layout.cell // 4)
    half = thick // 2
    for step, cell in enumerate(path):
        following = path[step + 1] if step + 1 < len(path) else cell
        x, y = layout.centre(*cell)
        other_x, other_y = layout.centre(*following)
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
    new maze has a new route, and a caption naming its seed is only
    true of that maze. So regenerating hands back one of these rather
    than three things the window would have to keep in step.
    """

    maze: Maze
    path: Path = ()
    title: str = ""
    message: Sequence[str] = ()


class MazeWindow:
    """A window showing one maze, and the keys that change it.

    MLX owns the loop once it is started, so it also owns when things
    are drawn: this class hands it a few callbacks and never draws of
    its own accord. ``draw`` is one of them, hooked to expose, which
    is what makes the drawing survive being covered up and uncovered.

    What the keys do to the maze itself is not this window's to
    decide. ``new_scene`` is the way out of that: whoever opens the
    window says what a new maze is, and R asks for one.
    """

    def __init__(self, scene: Scene, skin: Skin = STANDARD_SKIN,
                 new_scene: Callable[[], Scene] | None = None) -> None:
        # Imported here rather than at the top of the file: MLX is
        # only needed by a program that opens a window, and the rest
        # of this module is drawing anyone can read and test without
        # the library installed.
        from mlx import Mlx

        self.mlx = Mlx()
        self.mlx_ptr = self.mlx.mlx_init()
        self.scene = scene
        self.skin = skin
        self.new_scene = new_scene
        self.show_path = False
        self.wall_colour = 0
        self.forty_two_colour = 0

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
        self.mlx.mlx_expose_hook(self.window, self.draw, None)
        self.mlx.mlx_key_hook(self.window, self._on_key, None)
        self.mlx.mlx_hook(self.window, DESTROY_NOTIFY, 0, self._on_close,
                          None)
        # Drawn once here as well: the window is on screen by now, and
        # whether its first expose event reaches the hook above is the
        # server's business rather than something to rely on.
        self.draw()
        self.mlx.mlx_loop(self.mlx_ptr)
        self.mlx.mlx_destroy_image(self.mlx_ptr, self.canvas.image)
        self.mlx.mlx_destroy_window(self.mlx_ptr, self.window)
        self.mlx.mlx_release(self.mlx_ptr)

    def draw(self, _param: Any = None) -> None:
        """Draw everything: the maze as an image, the text over it.

        The maze goes into the image because that is one drawing
        handed to the window in one go. The text cannot: MLX writes
        strings on a window, never into an image, so it is written
        afterwards or it would be written under the maze.
        """
        draw(self.canvas, self.scene.maze, self.layout, self.skin,
             self.scene.path if self.show_path else ())
        self.mlx.mlx_put_image_to_window(self.mlx_ptr, self.window,
                                         self.canvas.image, 0, 0)
        self._write(self.scene.title, HEAD - LINE, self.skin.title)
        bottom = self.layout.window[1] - TAIL
        lines = [*self.scene.message, "", KEYS][-TAIL_LINES:]
        for number, text in enumerate(lines):
            self._write(text, bottom + (number + 1) * LINE,
                        self.skin.message)

    def _write(self, text: str, baseline: int, ink: Colour) -> None:
        """Write one line of text, centred as closely as MLX allows."""
        if not text:
            return
        line = ascii_only(text)
        width = self.layout.window[0]
        left = max(0, (width - len(line) * CHARACTER) // 2)
        self.mlx.mlx_string_put(self.mlx_ptr, self.window, left, baseline,
                                ink, line)

    def _on_key(self, keysym: int, _param: Any = None) -> None:
        """Answer one key press.

        MLX reports X keysyms, and the keysym of a printable key is
        the character code of what it types. So one ``chr`` turns the
        number into the letter on the keycap, and the keys below can
        be written as themselves instead of as a table of numbers.
        """
        key = chr(keysym).lower() if 32 <= keysym <= 126 else ""
        if keysym == ESCAPE or key == "q":
            self.mlx.mlx_loop_exit(self.mlx_ptr)
            return
        if key == "r" and self.new_scene is not None:
            self.scene = self.new_scene()
        elif key == "p":
            self.show_path = not self.show_path
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
        else:
            return
        self.draw()

    def _on_close(self, _param: Any = None) -> None:
        """Leave when the window's close button is pressed."""
        self.mlx.mlx_loop_exit(self.mlx_ptr)


def show(scene: Scene, skin: Skin = STANDARD_SKIN,
         new_scene: Callable[[], Scene] | None = None) -> None:
    """Open a window on that maze and run until the user leaves."""
    MazeWindow(scene, skin, new_scene).run()


__all__ = ["Canvas", "Layout", "MazeWindow", "Scene", "Skin",
           "STANDARD_SKIN", "TooSmall", "ascii_only", "colour", "draw",
           "show", "KEYS", "WALL_COLOURS", "FORTY_TWO_COLOURS"]
