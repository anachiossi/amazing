"""Colours for the terminal, chosen by name instead of by number.

A terminal writes each character with two colours: the **ink** the
symbol is drawn in, and the **paper** behind it. Both are asked for by
number, 0 to 255, which nobody remembers. This package gives every one
of those numbers a name.

    >>> from rainbow import ink, paper, write
    >>> ink("vermilion")
    '38;5;196'
    >>> paper("blackberry")
    '48;5;53'
    >>> print(write("careful", ink="vermilion", paper="soot"))

Every colour is named after the pigment, paint or dye it is: the
earths, the minerals, the plant lakes and the plain words painters
have always used — ``vermilion``, ``ochre``, ``terreverte``,
``ultramarine``, ``mauveine``, ``lampblack``. The sixteen a terminal
has always had keep their old names: ``black``, ``red``, ``lime``…

``python3 -m rainbow`` prints them all in their own colours, which is
the quickest way to choose one.

Anywhere a name is asked for, a number does just as well, so
``ink(196)`` and ``ink("vermilion")`` are the same thing.
"""

import difflib

from .palette import NAMES, NUMBERS, distance, rgb_of

__all__ = ["ink", "paper", "write", "number", "name", "nearest",
           "rgb_of", "NAMES", "NUMBERS", "RESET", "UnknownColour"]

# What ends a run of colour: back to the terminal's own.
RESET = "\033[0m"


class UnknownColour(Exception):
    """Raised for a name this palette does not have."""


def number(colour: str | int) -> int:
    """Return the palette number of a colour, given its name or number.

    An unknown name is an error rather than a default, and the message
    suggests the closest names there are — a colour picked by name is
    usually a colour typed from memory.
    """
    if isinstance(colour, int):
        if not 0 <= colour <= 255:
            raise UnknownColour(f"a colour is 0 to 255, got {colour}")
        return colour
    key = colour.strip().lower().replace(" ", "").replace("_", "")
    key = key.replace("-", "").replace("gray", "grey")
    if key in NAMES:
        return NAMES[key]
    close = difflib.get_close_matches(key, NAMES, n=3)
    hint = f", did you mean {' or '.join(close)}?" if close else ""
    raise UnknownColour(f"no colour called {colour!r}{hint}")


def name(colour: int) -> str:
    """Return the name to show for a palette number."""
    return NUMBERS[number(colour)]


def ink(colour: str | int) -> str:
    """Return the code that writes the symbol in that colour."""
    return f"38;5;{number(colour)}"


def paper(colour: str | int) -> str:
    """Return the code that puts that colour behind the symbol."""
    return f"48;5;{number(colour)}"


def write(text: str, ink: str | int | None = None,
          paper: str | int | None = None) -> str:
    """Return the text wrapped in the escape that colours it.

    Neither colour is required: text with no colour at all comes back
    untouched, so this can be called on everything without checking.
    """
    parts = []
    if ink is not None:
        parts.append(f"38;5;{number(ink)}")
    if paper is not None:
        parts.append(f"48;5;{number(paper)}")
    if not parts or not text:
        return text
    return f"\033[{';'.join(parts)}m{text}{RESET}"


def nearest(red: int, green: int, blue: int) -> int:
    """Return the palette colour closest to a red, green, blue mix.

    For when a colour is known as a value rather than as a name — from
    a design, an image, a website. Distance is measured the way the eye
    weighs the three parts rather than as plain arithmetic, so the
    answer is the colour that *looks* closest.
    """
    for value in (red, green, blue):
        if not 0 <= value <= 255:
            raise ValueError(f"red, green and blue are 0 to 255, got "
                             f"{red}, {green}, {blue}")
    # The sixteen basic colours are skipped: they are the terminal's
    # own and may not look like their values on someone else's screen.
    return min(range(16, 256),
               key=lambda candidate: distance(rgb_of(candidate),
                                              (red, green, blue)))
