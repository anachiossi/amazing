"""Tests for deciding how big to draw a maze.

Run from the repository root::

    python3 -m unittest discover -s tests -t .

How big a drawing is, which cell width fits a given space, and which
skin suits that width are all the renderer's own — asked of it here
with a size made up on the spot, so nothing depends on the terminal
these tests run in. What is left in ``a_maze_ing.py`` is where the
size comes from and what to do when nothing fits.
"""

import re
import unittest

from app.render.terminal import (BLOCKS, CELL_WIDTH, COMPACT, STANDARD_SKIN,
                                 Drawing, Frame, TooSmall, drawing_size,
                                 render, skin_for, widest_that_fits)
from mazegen import Maze

FRAME = Frame(head=2, tail=3, sides=2)


def plain(drawing: str) -> str:
    """Return a drawing with its escape sequences taken out.

    A drawing is always coloured, and the escapes are characters too —
    so anything measuring *width* has to take them off first.
    """
    return re.sub(r"\033\[[0-9;]*m", "", drawing)


class SizeTest(unittest.TestCase):
    """How much room a drawing takes."""

    def test_it_matches_the_drawing(self) -> None:
        """The size promised is the size drawn.

        Measured off the drawing itself rather than against the same
        formula twice, which is the whole reason this lives beside
        ``render``.
        """
        for width, height, cell_width in ((20, 15, 3), (4, 2, 1),
                                          (7, 9, 2)):
            with self.subTest(width=width, height=height):
                columns, lines = drawing_size(width, height, cell_width,
                                              FRAME)
                drawn = plain(render(Maze(width, height),
                                     Drawing(cell_width=cell_width,
                                             frame=FRAME))).split("\n")
                self.assertEqual(len(drawn), lines)
                self.assertEqual({len(line) for line in drawn}, {columns})

    def test_a_wider_cell_takes_more_room(self) -> None:
        """Nothing else changes, so only the columns grow."""
        narrow = drawing_size(10, 5, 1, FRAME)
        wide = drawing_size(10, 5, 3, FRAME)
        self.assertGreater(wide[0], narrow[0])
        self.assertEqual(wide[1], narrow[1])


class FitTest(unittest.TestCase):
    """Choosing the widest cell that fits a given space."""

    def test_a_roomy_space_gets_the_full_width(self) -> None:
        """With room to spare, cells are drawn at their full width."""
        self.assertEqual(widest_that_fits(20, 15, (120, 40), FRAME),
                         CELL_WIDTH)

    def test_it_never_goes_wider_than_asked(self) -> None:
        """A huge terminal does not stretch a small maze into air."""
        self.assertEqual(widest_that_fits(4, 3, (400, 100), FRAME),
                         CELL_WIDTH)

    def test_each_width_where_it_is_the_widest_that_fits(self) -> None:
        """One column short of a width is the next one down."""
        for cell_width in (3, 2, 1):
            columns, lines = drawing_size(20, 15, cell_width, FRAME)
            with self.subTest(cell_width=cell_width):
                self.assertEqual(
                    widest_that_fits(20, 15, (columns, lines), FRAME),
                    cell_width)
                if cell_width > 1:
                    self.assertLess(
                        widest_that_fits(20, 15, (columns - 1, lines),
                                         FRAME),
                        cell_width)

    def test_what_fits_really_fits(self) -> None:
        """The drawing at the chosen width is never wider than asked."""
        for columns in range(45, 130, 7):
            with self.subTest(columns=columns):
                cell_width = widest_that_fits(20, 15, (columns, 40), FRAME)
                drawn = plain(render(Maze(20, 15),
                                     Drawing(cell_width=cell_width,
                                             frame=FRAME)))
                widest = max(len(line) for line in drawn.split("\n"))
                self.assertLessEqual(widest, columns)

    def test_too_narrow_is_refused(self) -> None:
        """When not even one character a cell fits, say so."""
        with self.assertRaises(TooSmall):
            widest_that_fits(20, 15, (44, 40), FRAME)

    def test_too_short_is_refused(self) -> None:
        """Lines are fixed: no cell width can save a short screen."""
        with self.assertRaises(TooSmall):
            widest_that_fits(20, 15, (200, 35), FRAME)

    def test_the_message_says_what_is_needed_and_what_there_is(self
                                                              ) -> None:
        """The error is the one thing whoever called can act on."""
        with self.assertRaises(TooSmall) as raised:
            widest_that_fits(20, 15, (30, 10), FRAME)
        message = str(raised.exception)
        columns, lines = drawing_size(20, 15, 1, FRAME)
        self.assertIn(str(columns), message)
        self.assertIn(str(lines), message)
        self.assertIn("30", message)
        self.assertIn("10", message)


class SkinTierTest(unittest.TestCase):
    """Which skin goes with which width."""

    def test_letters_while_there_is_room_for_them(self) -> None:
        """Two characters wide still fits a symbol and its walls."""
        self.assertIs(skin_for(CELL_WIDTH), STANDARD_SKIN)
        self.assertIs(skin_for(COMPACT), STANDARD_SKIN)

    def test_blocks_when_there_is_not(self) -> None:
        """One character wide has nowhere to draw a line."""
        self.assertIs(skin_for(1), BLOCKS)

    def test_every_width_that_fits_gets_a_skin_that_reads(self) -> None:
        """The pair holds across the whole range, not just at one size.

        ``widest_that_fits`` may hand back 1, and a line skin drawn
        that narrow has no room to turn a corner. This is the check
        that the two agree — the reason they live side by side.
        """
        for columns in range(16, 96, 5):
            for lines in range(10, 44, 3):
                try:
                    width = widest_that_fits(8, 5, (columns, lines), FRAME)
                except TooSmall:
                    continue
                with self.subTest(columns=columns, lines=lines):
                    self.assertIs(skin_for(width),
                                  BLOCKS if width == 1 else STANDARD_SKIN)

    def test_the_block_skin_still_marks_the_ends(self) -> None:
        """A cell one character wide holds one symbol, so it keeps it."""
        self.assertTrue(BLOCKS.entry.symbol.strip())
        self.assertTrue(BLOCKS.exit.symbol.strip())
        self.assertNotEqual(BLOCKS.entry.symbol, BLOCKS.exit.symbol)


if __name__ == "__main__":
    unittest.main()
