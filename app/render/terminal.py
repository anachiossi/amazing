"""Minimalist rendering on terminal.

The maze is read through two methods only, ``get_dim`` and
``get_wall``. Only reads, never writes.

Line by line, top to bottom, left to right, appended to a string.

A maze of WIDTH x HEIGHT becomes ``2 * HEIGHT + 1`` lines::

    ┏━━━┳━━━━━━━┓      a wall line: junctions, and the walls above
    ┃ E │       ┃      a cell line: walls beside the cells, and their
    ┣━━━┿━━━┓   ┃                   insides
    ┃       │  X┃
    ┗━━━┻━━━┻━━━┛      one last wall line closes the bottom

The border is drawn first: the outside of a maze is always walled,
so those four edges are drawn without asking the maze anything.

What is left is inside, and a wall in there sits between two cells:
if every cell drew all four of its sides, every wall would be drawn
twice.

So each cell only draws two walls — N and W. No exception, because
the walls that no cell would draw are the border, and the border is
already there.

┌───┬───┐     A, B, C and D each draw their own N and W.
│ A │ B │
├───┼───┤     B's E and D's S belong to no cell — nobody would ever
│ C │ D │     draw them. They are the border, drawn first.
└───┴───┘

What is around the maze
-----------------------

The maze sits in a **canvas**: an area with a head for the title and
a tail for messages.

Colour
------

Uncoloured is not available: an ``Element`` is a shape and a colour
together. Every colour is ink — there are no backgrounds, because one
character holds one thing.

A cell walled in on all four sides is drawn like any other; the "42"
shows as the boxes it is made of, with no special element of its own.

"""

import re
import shutil
import sys
import termios
import textwrap
import time
import tty
from dataclasses import dataclass, field, replace
from typing import Iterable, Sequence

import rainbow
from mazegen import Cell, Direction, Maze, Path, Paths

# What a cell on a path knows: the sides it links to, and the element
# of the path that drew it.
Link = tuple[int, "JoinedElement"]

# A cell is this many characters wide unless asked otherwise. Three,
# because a terminal character is about twice as tall as it is wide:
# at 1 a square maze comes out flattened.
CELL_WIDTH = 3

# The widths a fit may choose between. One, now that there is one
# skin: the box-drawing needs room to turn a corner, so a cell
# narrower than this is not a tighter drawing but an unreadable one.
WIDTHS = (CELL_WIDTH,)


@dataclass(frozen=True)
class Element:
    """A symbol, and the ink it is written in.

    ``ink`` is an ANSI code, written as it appears inside the escape
    sequence that wraps the text::

        ink = "38;5;N"    write the symbol in colour N

    **38** means ink; **5** means "pick from the 256-colour palette by
    number"; **N** is that number, 0 to 255. ``rainbow`` turns a name
    into one of these, so nothing here is a bare number.

    Empty ink means the terminal's own colour, which is what most of a
    drawing is written in.
    """

    symbol: str = " "
    ink: str = ""


@dataclass(frozen=True)
class JoinedElement(Element):
    """The symbol depends on the neighbours.

    Walls, borders and the path are all drawn as lines, so which piece
    to use — ``─``, ``┐``, ``┼`` — is only known once the neighbours
    are known. ``joints`` holds the sixteen pieces, indexed by the
    sides the piece reaches towards, using the bits ``Direction``
    already defines: N = 1, E = 2, S = 4, W = 8. Index 10 is E | W,
    wall on the left and wall on the right, so a horizontal line.
    Index 0 is a piece that touches nothing, and is left blank.
    """

    joints: str = " " * 16

    def __post_init__(self) -> None:
        """Refuse a table that cannot answer every junction."""
        if len(self.joints) != 16:
            raise ValueError(
                f"joints needs one symbol per junction, that is 16, "
                f"got {len(self.joints)}"
            )

    def piece(self, sides: int) -> str:
        """What piece to use for a junction with those sides."""
        return self.joints[sides]

    def straight(self, direction: Direction) -> str:
        """What piece to use for a straight line in that direction?"""
        if direction in (Direction.N, Direction.S):
            return self.joints[Direction.N | Direction.S]
        return self.joints[Direction.E | Direction.W]


@dataclass(frozen=True)
class Frame:
    """The canvas around the maze: head, tail and sides."""

    head: int = 2
    tail: int = 3
    sides: int = 2


@dataclass(frozen=True)
class TerminalSkin:
    """A reusable set of elements.

    A new look is a new instance of this class, with the same elements
    but different symbols and colours.
    """

    floor: Element
    wall: JoinedElement
    border: JoinedElement
    entry: Element
    exit: Element
    paths: tuple[JoinedElement, ...]
    title: Element
    message: Element
    meeting: JoinedElement | None = None
    char1: Element | None = None
    char2: Element | None = None

    # What stands in a cell of the "42". The shape shows without it —
    # it is a block nothing runs through — but a cell filled in reads
    # as solid rather than as somewhere not yet carved.
    forty_two: Element | None = None


STANDARD_SKIN = TerminalSkin(
    floor=Element(" "),
    wall=JoinedElement(ink=rainbow.ink("chambray"),
                       joints=" ╵╶└╷│┌├╴┘─┴┐┤┬┼"),
    border=JoinedElement(ink=rainbow.ink("cloud"),
                         joints=" ╹╺┗╻┃┏┠╸┛━┷┓┨┯╋"),
    paths=(JoinedElement(ink=rainbow.ink("gamboge"),
                         joints="•╵╶╰╷│╭├╴╯─┴╮┤┬┼"),
           JoinedElement(ink=rainbow.ink("manganese"),
                         joints="•╵╶╰╷│╭├╴╯─┴╮┤┬┼")),
    meeting=JoinedElement(ink=rainbow.ink("verdigris"),
                          joints="•╵╶╰╷│╭├╴╯─┴╮┤┬┼"),
    entry=Element("⬤", ink=rainbow.ink("peppermint")),
    exit=Element("⚑", ink=rainbow.ink("madder")),
    title=Element(ink=rainbow.ink("snow")),
    message=Element(ink=rainbow.ink("stone")),
    char1=Element("இ", ink=rainbow.ink("cadmium")),
    char2=Element("&", ink=rainbow.ink("flamingo")),
    forty_two=Element("ဩ", ink=rainbow.ink("robin")),
)

FRAME = Frame()


@dataclass
class Drawing:
    """Everything a rendering needs to draw.

    ``paths`` is a list of routes, drawn one element each; a single
    search is simply a list of one.

    The two ends are not here: they are the maze's, and ``render``
    reads them from it.

    ``skin`` left alone means "whatever suits ``cell_width``", so a
    line skin cannot be paired with a cell one character wide by
    forgetting to say otherwise. Naming one still wins.

    ``fit`` asks for the widest cell that fits the space instead of
    the one named. It is off by default: fitting reads the terminal,
    and a drawing that did so unasked would come out differently in
    every window it was made in.
    """

    paths: Paths = ()
    char1: Cell | None = None
    char2: Cell | None = None
    title: str = ""
    message: Sequence[str] = ()
    skin: TerminalSkin | None = None
    frame: Frame = FRAME
    cell_width: int = CELL_WIDTH
    fit: bool = False

    # What ``fit_to`` settled on, kept apart from what was asked for
    # above so that a window growing back gets its title back: the
    # request is the thing that lasts, the fit is redone every draw.
    shown_frame: Frame | None = field(default=None, init=False, repr=False)
    shown_message: Sequence[str] | None = field(default=None, init=False,
                                                repr=False)

    def fit_to(self, maze: Maze) -> int:
        """Settle the cell width for that maze, and return it.

        Without ``fit`` the width already named stands. With it, the
        widest that fits the space is worked out and kept, so that
        afterwards ``cell_width`` is what will actually be drawn.

        ``render`` calls this itself. It is public because whoever
        wants to say how big the drawing came out — a caption naming
        the size, say — has to ask before the drawing is made, and
        should get the same answer rather than working it out again.

        Raises ``TooSmall`` when no width fits, which is the caller's
        to answer: there is no drawing to make.
        """
        self.shown_frame, self.shown_message = self.frame, self.message
        if self.fit:
            width, height = maze.get_dim()
            self.cell_width, self.shown_frame, self.shown_message = fitted(
                width, height, frame=self.frame, message=self.message)
        return self.cell_width

    def drawn_with(self) -> TerminalSkin:
        """The skin named, or the one every drawing gets by default."""
        return self.skin if self.skin is not None else STANDARD_SKIN


def horizontal(maze: Maze, col: int, row: int) -> bool:
    """Is there a horizontal wall segment above cell (col, row)?

    The N and S edges of the maze are walled by definition; inside,
    the segment is the north wall of the cell below it.
    """
    width, height = maze.get_dim()
    if not (0 <= col < width and 0 <= row <= height):
        return False
    if row in (0, height):
        return True
    return maze.get_wall(col, row, Direction.N)


def vertical(maze: Maze, col: int, row: int) -> bool:
    """Is there an upright wall segment left of cell (col, row)?

    The W and E edges of the maze are walled by definition; inside,
    the segment is the west wall of the cell to its right.
    """
    width, height = maze.get_dim()
    if not (0 <= row < height and 0 <= col <= width):
        return False
    if col in (0, width):
        return True
    return maze.get_wall(col, row, Direction.W)


def path_links(path: Path) -> dict[Cell, int]:
    """The shape of the path line going in and out of each cell?

    The path is the route the solver walks, entry to exit. This gives
    its shape in each cell, so the renderer can draw it as a line: the
    sides it links to, added together, are the number that picks the
    piece — the same sixteen the walls are drawn with.
    """
    sides: dict[Cell, int] = {}
    for index, cell in enumerate(path):
        reaches = 0
        for other in (path[index - 1] if index else None,
                      path[index + 1] if index + 1 < len(path) else None):
            if other is None:
                continue
            for side in Direction:
                step_col, step_row = side.step()
                if (cell[0] + step_col, cell[1] + step_row) == other:
                    reaches |= side
        sides[cell] = reaches
    return sides


def paths_links(paths: Paths, elements: Sequence[JoinedElement],
                meeting: JoinedElement | None = None,
                goal: Cell | None = None) -> dict[Cell, Link]:
    """Merge links from several paths, including shared cells.

    Each path is drawn in its own element — the first path takes the
    first of them, the second the second, round again if there are
    more paths than elements.

    **Until it is solved.** Two things say that: a cell more than one
    path runs through, meaning the searches have found each other, or
    a path reaching ``goal``, meaning one of them got there on its own.
    Either way the routes stop being separate attempts and become the
    answer, so every cell of every path is drawn in the meeting
    element — two colours right up to that step, one colour from it on.

    Where paths share a cell the sides add up, so the cell links every
    way any of them leaves by.
    """
    sides_of: dict[Cell, int] = {}
    walked_by: dict[Cell, set[int]] = {}
    for index, path in enumerate(paths):
        for cell, sides in path_links(path).items():
            sides_of[cell] = sides_of.get(cell, 0) | sides
            walked_by.setdefault(cell, set()).add(index)

    solved = (any(len(walkers) > 1 for walkers in walked_by.values())
              or (goal is not None and goal in sides_of))
    links: dict[Cell, Link] = {}
    for cell, sides in sides_of.items():
        if solved and meeting is not None:
            element = meeting
        else:
            element = elements[min(walked_by[cell]) % len(elements)]
        links[cell] = (sides, element)
    return links


def paint(text: str, element: Element) -> str:
    """Return the text wrapped in colors."""
    if not text:
        return text
    return f"\033[{element.ink}m{text}\033[0m" if element.ink else text


# ---------------------------------------------------------------------
# The maze itself: one wall line and one cell line per row.


def junction(maze: Maze, col: int, row: int,
             skin: TerminalSkin) -> tuple[str, Element]:
    """Return the piece that belongs where four walls could meet."""

    width, height = maze.get_dim()
    sides = 0
    if vertical(maze, col, row - 1):
        sides |= Direction.N
    if vertical(maze, col, row):
        sides |= Direction.S
    if horizontal(maze, col, row):
        sides |= Direction.E
    if horizontal(maze, col - 1, row):
        sides |= Direction.W
    on_frame = col in (0, width) or row in (0, height)
    element = skin.border if on_frame else skin.wall
    return element.piece(sides), element


def _horizontal_line(maze: Maze, row: int, plan: Drawing,
                     links: dict[Cell, Link]) -> str:
    """Return the horizontal line that runs above a row of cells.

    Every junction, and between them the wall that the cell above and
    the cell below share. There is one more of these lines than there
    are rows: ``_horizontal_line(0)`` is the top of the maze and
    ``_horizontal_line(height)`` is the bottom.

    Where there is no wall the floor shows through, and the path
    crosses the opening if it goes that way — north to south, because
    an opening in a wall that runs across is passed through up and
    down.
    """

    skin, cell_width = plan.drawn_with(), plan.cell_width
    width, height = maze.get_dim()
    out = []
    for col in range(width + 1):
        symbol, element = junction(maze, col, row, skin)
        out.append(paint(symbol, element))
        if col == width:
            break
        if horizontal(maze, col, row):
            element = skin.border if row in (0, height) else skin.wall
            out.append(paint(element.straight(Direction.E) * cell_width,
                             element))
        else:
            out.append(_opening(skin, cell_width, Direction.N,
                                _crossing(links, (col, row), Direction.N)))
    return "".join(out)


def _centre_line(maze: Maze, row: int, plan: Drawing,
                 links: dict[Cell, Link],
                 marks: dict[Cell, Element]) -> str:
    """Return the line through a row: its walls and its centres.

    The wall standing beside each cell, and then the inside of the
    cell — floor, the path, whatever mark stands there. One of these
    lines per row, alternating with the lines above them.

    An opening here is in a wall that stands upright, so the path
    crosses it east to west.
    """
    skin = plan.drawn_with()
    width, _ = maze.get_dim()
    out = []
    for col in range(width + 1):
        if vertical(maze, col, row):
            element = skin.border if col in (0, width) else skin.wall
            out.append(paint(element.straight(Direction.N), element))
        else:
            out.append(_opening(skin, 1, Direction.W,
                                _crossing(links, (col, row), Direction.W)))
        if col == width:
            break
        out.append(_inside(col, row, plan, links, marks))
    return "".join(out)


def line(maze: Maze, char_row: int, plan: Drawing,
         links: dict[Cell, Link],
         marks: dict[Cell, Element]) -> str:
    """Return one line of the maze, whichever kind it is.

    A 2x2 maze is five lines, and they alternate::

        char_row 0   ┏━━━┯━━━┓   even — horizontal lines and junctions
        char_row 1   ┃ E │   ┃   odd  — walls, and the centres of cells
        char_row 2   ┠───┼───┨   even
        char_row 3   ┃   │ X ┃   odd
        char_row 4   ┗━━━┷━━━┛   even

    The centres are where anything that is not a wall goes: the floor,
    the path, E and X. So the even lines are drawn by
    ``_horizontal_line`` and the odd ones by ``_centre_line``, and
    ``divmod`` says which is which and which row of cells it belongs
    to::

        divmod(3, 2) -> (1, 1)   row 1, odd   the centres of row 1
        divmod(4, 2) -> (2, 0)   row 2, even  the horizontal above row
                                              2, the bottom edge

    """
    row, kind = divmod(char_row, 2)
    if kind:
        return _centre_line(maze, row, plan, links, marks)
    return _horizontal_line(maze, row, plan, links)


def _inside(col: int, row: int, plan: Drawing,
            links: dict[Cell, Link],
            marks: dict[Cell, Element]) -> str:
    """Return the inside of one cell: everything that is not a wall.

    Three pieces — the middle, where a mark or the path stands, and a
    stretch either side of it where the path runs out towards the
    cells it links to::

        "   "    nothing here
        " E "    entry symbol stands here
        "───"    the path runs straight through
        "─╮ "    the path arrives from the west and turns south

    A cell walled in on all four sides gets no special treatment: it
    is the walls around it that make the "42" show.
    """
    skin, cell_width = plan.drawn_with(), plan.cell_width
    cell = (col, row)
    middle = cell_width // 2
    sides, element = links.get(cell, (0, None))
    return (_stretch(middle, skin, element if sides & Direction.W else None)
            + _middle(skin, cell, marks, links)
            + _stretch(cell_width - middle - 1, skin,
                       element if sides & Direction.E else None))


def _middle(skin: TerminalSkin, cell: Cell, marks: dict[Cell, Element],
            links: dict[Cell, Link]) -> str:
    """Return the character in the middle of a cell.

    Priority:
    a mark beats the path,
    and the path beats the floor.
    """
    if cell in marks:
        return paint(marks[cell].symbol, marks[cell])
    if cell in links:
        sides, element = links[cell]
        return paint(element.piece(sides), element)
    return paint(skin.floor.symbol, skin.floor)


def _stretch(span: int, skin: TerminalSkin,
             path: JoinedElement | None) -> str:
    """Return the path running out of a cell, or the floor."""
    if path is None:
        return paint(skin.floor.symbol * span, skin.floor)
    return paint(path.straight(Direction.E) * span, path)


def _opening(skin: TerminalSkin, span: int, through: Direction,
             crossing: JoinedElement | None) -> str:
    """What to draw where a wall is missing: the path, or the floor.

    ``through`` is the way the opening is passed: north for a gap in a
    wall that runs across, west for a gap in one that stands upright.
    It is the caller's to say — at a cell one character wide the two
    kinds of opening are the same width, so the span cannot tell them
    apart.
    """
    if crossing is None:
        return paint(skin.floor.symbol * span, skin.floor)
    piece = crossing.straight(through)
    middle = span // 2
    return (paint(skin.floor.symbol * middle, skin.floor)
            + paint(piece, crossing)
            + paint(skin.floor.symbol * (span - middle - 1), skin.floor))


def _crossing(links: dict[Cell, Link], cell: Cell,
              side: Direction) -> JoinedElement | None:
    """Return the path that crosses the opening on that side, if any.

    Asked from both sides of the opening: this cell may link that way,
    or the cell beyond it may link back. Either answer is the same
    crossing, and the element that comes with it says which path made
    it — so two searches keep their own colours right up to the
    opening each came through.
    """
    step_col, step_row = side.step()
    other = (cell[0] + step_col, cell[1] + step_row)
    sides, element = links.get(cell, (0, None))
    if sides & side:
        return element
    sides, element = links.get(other, (0, None))
    if sides & side.opposite():
        return element
    return None


def wrap(text: str, width: int) -> list[str]:
    """Break a message into as many lines as it takes to keep all of it.

    A message that already fits comes back untouched, spacing and all:
    the action bar spaces its keys out on purpose, and squeezing that
    out of a line with room to spare would be a change nobody asked
    for. Only when it does not fit is the spacing spent, a word at a
    time — because the alternative was cutting the line off, and a key
    the reader cannot see is a key they do not have.
    """
    if width < 1 or len(text) <= width:
        return [text]
    return textwrap.wrap(text, width, break_long_words=True,
                         break_on_hyphens=False) or [""]


def message_lines(message: Sequence[str], canvas: int,
                  frame: Frame) -> list[str]:
    """The lines under the maze: every message, wrapped to the canvas.

    ``frame.tail`` is a floor rather than a count. Fewer messages than
    that are padded out with blanks, so the drawing keeps its shape
    from one frame to the next and nothing jumps; more, or messages
    long enough to wrap, make the tail taller instead of being cut.
    """
    lines = [line for text in message for line in wrap(text, canvas)]
    return lines + [""] * (frame.tail - len(lines))


def band(text: str, width: int, element: Element) -> str:
    """Return one line of canvas, with the text centred on it."""
    text = text[:width]
    left = (width - len(text)) // 2
    return (" " * left + paint(text, element)
            + " " * (width - left - len(text)))


# ---------------------------------------------------------------------
# And finally but not least, the render function.


class TooSmall(Exception):
    """Raised when no cell width makes a maze fit the space given."""


def too_small(width: int, height: int, needed: tuple[int, int],
              columns: int, lines: int) -> TooSmall:
    """The refusal, said in a way the reader can act on.

    Which way it is short, by how much, and what to do about it. A
    terminal is made bigger by making its text smaller, which is not
    the first thing that comes to mind when a program says there is
    not enough room — so it is the thing this says out loud.
    """
    short = []
    if needed[0] > columns:
        short.append(f"{needed[0] - columns} columns")
    if needed[1] > lines:
        short.append(f"{needed[1] - lines} lines")
    return TooSmall(
        f"a {width}x{height} maze needs at least {needed[0]} columns "
        f"x {needed[1]} lines, and there are {columns} x {lines} — "
        f"{' and '.join(short)} short. Press ctrl and minus to make the "
        f"text smaller: the window then holds more of both."
    )


def drawing_size(width: int, height: int, cell_width: int = CELL_WIDTH,
                 frame: Frame = FRAME,
                 tail: int | None = None) -> tuple[int, int]:
    """Return the columns and lines a drawing of that maze would take.

    Every cell needs its own width plus one character for the wall
    beside it, and one more closes the right-hand side; every row needs
    a line for its cells and one for the wall above, and one more
    closes the bottom. The frame is added to both.

    It lives here because it is the drawing's own arithmetic — anyone
    else who worked it out would be copying these numbers, and would
    have to be found and corrected every time they changed.
    """
    return (width * (cell_width + 1) + 1 + 2 * frame.sides,
            2 * height + 1 + frame.head
            + (frame.tail if tail is None else tail))


def squeezes(frame: Frame,
             message: Sequence[str]
             ) -> Iterable[tuple[Frame, Sequence[str]]]:
    """Ways to draw the same maze in less room, roomiest first.

    Only the frame is ever given up — the maze itself is what was
    asked for. The title goes before any message does, because a
    drawing with no name is still readable; then the messages go from
    the front, so whoever writes them puts the one that matters least
    first.

    The last message is never given up. It is the action bar, and keys
    the reader cannot see are keys they do not have.

    ``tail`` comes down with the messages. It is a floor rather than a
    count, so leaving it where it was would pad the lines straight
    back and give up the text for nothing.
    """
    yield frame, message
    if frame.head:
        yield replace(frame, head=0), message
    for keep in range(len(message) - 1, 0, -1):
        yield (replace(frame, head=0, tail=min(frame.tail, keep)),
               message[-keep:])


def fitted(width: int, height: int,
           space: tuple[int, int] | None = None,
           frame: Frame = FRAME,
           widest: int = CELL_WIDTH,
           message: Sequence[str] = ()
           ) -> tuple[int, Frame, Sequence[str]]:
    """The roomiest drawing of that maze that fits, as three answers.

    Two things can be spent, and they are spent in that order: the
    width of a cell first, since a narrower cell still draws
    everything, and only then the frame, since that is text taken off
    the screen. So a drawing gives up its title only once there is no
    cell width left to give up.

    ``space`` left out means the terminal this is running in, as with
    ``widest_that_fits``.
    """
    if space is None:
        size = shutil.get_terminal_size()
        columns, lines = size.columns, size.lines
    else:
        columns, lines = space
    for squeezed, shown in squeezes(frame, message):
        for cell_width in (w for w in WIDTHS if w <= widest):
            canvas = drawing_size(width, height, cell_width, squeezed)[0]
            tall = len(message_lines(shown, canvas, squeezed))
            needed = drawing_size(width, height, cell_width, squeezed, tall)
            if needed[0] <= columns and needed[1] <= lines:
                return cell_width, squeezed, shown
    raise too_small(width, height,
                    drawing_size(width, height, WIDTHS[-1], frame),
                    columns, lines)


def widest_that_fits(width: int, height: int,
                     space: tuple[int, int] | None = None,
                     frame: Frame = FRAME,
                     widest: int = CELL_WIDTH,
                     message: Sequence[str] = ()) -> int:
    """Return the widest cell that draws that maze inside ``space``.

    Try each of ``WIDTHS``, biggest first, and take the first that
    fits — the same arithmetic as ``drawing_size``, asked backwards,
    which is why the two belong together.

    ``space`` left out means the terminal this is running in, which is
    what a terminal renderer is drawing into and so is its own to ask.
    Handing one in keeps the answer a calculation rather than a
    question about the machine: tests pass a size made up on the spot,
    and a window can pass its own.

    Nothing fits: ``TooSmall``, with what it would need and what there
    is, since that is the one thing whoever called can act on.
    """
    if space is None:
        size = shutil.get_terminal_size()
        columns, lines = size.columns, size.lines
    else:
        columns, lines = space
    # The tail is asked for each candidate rather than once: a narrower
    # cell is a narrower canvas, and the same messages wrap to more
    # lines in it. Condensing buys columns and can cost lines.

    def needs(cell_width: int) -> tuple[int, int]:
        canvas = drawing_size(width, height, cell_width, frame)[0]
        tall = len(message_lines(message, canvas, frame))
        return drawing_size(width, height, cell_width, frame, tall)

    for cell_width in (w for w in WIDTHS if w <= widest):
        needed = needs(cell_width)
        if needed[0] <= columns and needed[1] <= lines:
            return cell_width
    raise too_small(width, height, needs(WIDTHS[-1]), columns, lines)


def render(maze: Maze, drawing: Drawing | None = None) -> str:
    """Draw a maze and return it as one string, ready to print."""
    plan = drawing or Drawing()
    plan.fit_to(maze)
    skin = plan.drawn_with()
    frame = plan.shown_frame if plan.shown_frame is not None else plan.frame
    message = (plan.shown_message if plan.shown_message is not None
               else plan.message)
    width, height = maze.get_dim()
    canvas, _ = drawing_size(width, height, plan.cell_width, frame)
    links = paths_links(plan.paths, skin.paths, skin.meeting,
                        maze.get_exit())
    marks: dict[Cell, Element] = {}
    # First, so that an end or a character standing on one of these
    # cells is drawn over the filling rather than under it.
    if skin.forty_two is not None:
        for filled in maze.get_frozen():
            marks[filled] = skin.forty_two
    for cell, element in ((plan.char1, skin.char1), (plan.char2, skin.char2),
                          (maze.get_entry(), skin.entry),
                          (maze.get_exit(), skin.exit)):
        if cell is not None and element is not None:
            marks[cell] = element

    body = [line(maze, char_row, plan, links, marks)
            for char_row in range(2 * height + 1)]

    side = " " * frame.sides
    out = [band("", canvas, skin.title) for _ in range(frame.head)]
    if plan.title and frame.head:
        out[frame.head // 2] = band(plan.title, canvas, skin.title)
    out.extend(side + drawn + side for drawn in body)
    for text in message_lines(message, canvas, frame):
        out.append(band(text, canvas, skin.message))
    return "\n".join(out)


def show(maze: Maze, drawing: Drawing | None = None) -> None:
    """Print a maze in colour, for a quick look."""
    print(render(maze, drawing))


def redraw(maze: Maze, drawing: Drawing | None = None) -> None:
    """Wipe the screen and print the maze, so the next frame sits on top."""
    clear_screen()
    show(maze, drawing)


def read_key() -> str:
    """Wait for one key, without requiring Enter."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


WALL_COLOURS = (
    "chambray",
    "vermilion",
    "gamboge",
    "peppermint",
    "ultramarine",
)


def palette_line(maze: Maze, drawing: Drawing) -> str:
    """Numbered swatches, centred on the same canvas as the message."""
    parts: list[str] = []
    for index, name in enumerate(WALL_COLOURS, start=1):
        swatch = rainbow.write("█", ink=name)
        parts.append(f"{index} {swatch} {name}")
    text = "  ".join(parts)
    width, height = maze.get_dim()
    columns, _ = drawing_size(width, height, drawing.cell_width,
                              drawing.frame)
    visible = len(re.sub(r"\033\[[0-9;]*m", "", text))
    left = max(0, (columns - visible) // 2)
    right = max(0, columns - left - visible)
    return " " * left + text + " " * right


def apply_wall_colour(drawing: Drawing, colour: str) -> None:
    """Repaint interior walls and the border in that colour."""
    base = drawing.drawn_with()
    ink = rainbow.ink(colour)
    drawing.skin = replace(
        base,
        wall=replace(base.wall, ink=ink),
        border=replace(base.border, ink=ink),
    )


# ---------------------------------------------------------------------
# Animation: the same drawing, again, over itself.


@dataclass
class AnimationFrame:
    """One animation snapshot: maze state together with its drawing."""

    maze: Maze
    drawing: Drawing = field(default_factory=Drawing)


def path_frames(maze: Maze, drawing: Drawing) -> Iterable[AnimationFrame]:
    """Yield snapshots that reveal every path one cell at a time.

    Each route grows by a cell per frame, which is what makes two
    halves of a bidirectional search meet on screen.
    """
    length = max((len(path) for path in drawing.paths), default=0)
    for end in range(length + 1):
        prefixes = tuple(path[:end] for path in drawing.paths)
        yield AnimationFrame(maze, replace(drawing, paths=prefixes))


def clear_screen() -> None:
    """Send the cursor home and wipe what is on the screen."""
    sys.stdout.write("\033[H\033[J")


def animate(frames: Iterable[Maze | AnimationFrame],
            drawing: Drawing | None = None,
            delay: float = 0.05, reveal: bool = True) -> None:
    """Draw one maze after another in place, as a moving picture.

    ``frames`` may be maze states, or snapshots containing a maze and
    its own drawing. Maze-only frames use the shared ``drawing``
    argument. When a drawing has paths, each maze state reveals them a
    cell at a time — unless ``reveal`` is False, which draws the frame
    as it is. That is how a finished route is held on screen: without
    it every call would grow the path again from nothing.

    A generator that yields itself after each change animates too::

        animate(generator.carve(), delay=0.02)

    The screen is cleared between frames rather than after, so what is
    left on screen at the end is the finished maze.
    """
    shared = drawing or Drawing()
    for frame in frames:
        if isinstance(frame, AnimationFrame):
            maze, plan = frame.maze, frame.drawing
        else:
            maze, plan = frame, shared
        snapshots = (path_frames(maze, plan)
                     if reveal and plan.paths
                     else (AnimationFrame(maze, plan),))
        for snapshot in snapshots:
            redraw(snapshot.maze, snapshot.drawing)
            time.sleep(delay)
