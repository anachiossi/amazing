"""Tests for deciding how big to draw a maze.

Run from the repository root::

    python3 -m unittest discover -s tests -t .

How big a drawing is, which cell width fits a given space, and which
skin suits that width are all the renderer's own — asked of it here
with a size made up on the spot, so nothing depends on the terminal
these tests run in. What is left in ``a_maze_ing.py`` is where the
size comes from and what to do when nothing fits.
"""

import os
import re
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from unittest.mock import patch

from app.render.terminal import (CELL_WIDTH, WIDTHS, STANDARD_SKIN,
                                 Drawing, Element, Frame, TooSmall,
                                 drawing_size, render, widest_that_fits)
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
        """Exactly enough room draws; one column less does not.

        There is a single width now, so one column short of it is not
        a narrower drawing — it is no drawing.
        """
        for cell_width in WIDTHS:
            columns, lines = drawing_size(20, 15, cell_width, FRAME)
            with self.subTest(cell_width=cell_width):
                self.assertEqual(
                    widest_that_fits(20, 15, (columns, lines), FRAME),
                    cell_width)
                with self.assertRaises(TooSmall):
                    widest_that_fits(20, 15, (columns - 1, lines), FRAME)

    def test_what_fits_really_fits(self) -> None:
        """The drawing at the chosen width is never wider than asked."""
        for columns in range(85, 130, 7):
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
        columns, lines = drawing_size(20, 15, CELL_WIDTH, FRAME)
        self.assertIn(str(columns), message)
        self.assertIn(str(lines), message)
        self.assertIn("30", message)
        self.assertIn("10", message)

    def test_the_message_says_which_way_it_is_short(self) -> None:
        """Both numbers are there; only one of them is the problem."""
        with self.assertRaises(TooSmall) as raised:
            widest_that_fits(20, 15, (200, 30), FRAME)
        self.assertIn("6 lines short", str(raised.exception))
        with self.assertRaises(TooSmall) as raised:
            widest_that_fits(20, 15, (60, 40), FRAME)
        self.assertIn("25 columns short", str(raised.exception))

    def test_the_message_says_what_to_do_about_it(self) -> None:
        """A terminal holds more when its text is smaller, so say so."""
        with self.assertRaises(TooSmall) as raised:
            widest_that_fits(20, 15, (30, 10), FRAME)
        self.assertIn("ctrl and minus", str(raised.exception))


class DefaultSpaceTest(unittest.TestCase):
    """Left to itself, the renderer asks the terminal how big it is."""

    @contextmanager
    def fake_terminal(self, columns: int,
                      lines: int) -> Iterator[None]:
        """Stand in for the terminal the renderer would ask."""
        with patch("shutil.get_terminal_size",
                   return_value=os.terminal_size((columns, lines))):
            yield

    def test_no_space_reads_the_terminal(self) -> None:
        """Omitting the space is the same as passing what it would read."""
        for columns in (120, 100, 86):
            with self.subTest(columns=columns):
                with self.fake_terminal(columns, 40):
                    self.assertEqual(
                        widest_that_fits(20, 15),
                        widest_that_fits(20, 15, (columns, 40)))

    def test_a_space_given_wins_over_the_terminal(self) -> None:
        """A caller with its own room is not overruled by the machine."""
        with self.fake_terminal(40, 12):
            self.assertEqual(widest_that_fits(20, 15, (200, 60)),
                             CELL_WIDTH)

    def test_a_terminal_too_small_still_raises(self) -> None:
        """The failure is the same whether the size was read or given."""
        with self.fake_terminal(30, 10):
            with self.assertRaises(TooSmall):
                widest_that_fits(20, 15)


class DrawnWithTest(unittest.TestCase):
    """Which skin a drawing is drawn with when it does not say."""

    def test_a_drawing_that_says_nothing_gets_the_standard_skin(self) -> None:
        """There is one skin, and it is what a drawing gets."""
        self.assertIs(Drawing().drawn_with(), STANDARD_SKIN)
        self.assertIs(Drawing(cell_width=1).drawn_with(), STANDARD_SKIN)

    def test_a_skin_named_wins(self) -> None:
        """Saying which skin is still saying it, at any width."""
        other = replace(STANDARD_SKIN, floor=Element("."))
        self.assertIs(Drawing(skin=other).drawn_with(), other)
        self.assertIs(Drawing(cell_width=1, skin=other).drawn_with(), other)

    def test_it_is_the_skin_the_drawing_is_made_of(self) -> None:
        """Not just the answer: the symbols on screen follow it too."""
        other = replace(STANDARD_SKIN, floor=Element("."))
        drawing = plain(render(Maze(3, 2), Drawing(skin=other)))
        self.assertIn(".", drawing)


class FittedDrawingTest(unittest.TestCase):
    """A drawing asked to fit the space it is drawn into."""

    def test_off_by_default(self) -> None:
        """A drawing keeps the width it was given unless asked."""
        plan = Drawing()
        with patch("shutil.get_terminal_size",
                   return_value=os.terminal_size((45, 40))):
            self.assertEqual(plan.fit_to(Maze(20, 15)), CELL_WIDTH)
        self.assertEqual(plan.cell_width, CELL_WIDTH)

    def test_it_settles_the_width_against_the_space(self) -> None:
        """With fit, the widest that fits wins over the default.

        There is one width to settle on, so this says the fit reaches
        it rather than keeping whatever the drawing was made with.
        """
        for columns in (120, 90, 86):
            with self.subTest(columns=columns):
                plan = Drawing(fit=True, cell_width=1)
                with patch("shutil.get_terminal_size",
                           return_value=os.terminal_size((columns, 40))):
                    self.assertEqual(plan.fit_to(Maze(20, 15)), CELL_WIDTH)
                self.assertEqual(plan.cell_width, CELL_WIDTH)

    def test_the_width_is_kept_for_whoever_asks_after(self) -> None:
        """The caption reads the same number that was drawn.

        This is why ``fit_to`` is public: the message under the maze
        is written before the maze is, and must not work the size out
        a second time.
        """
        plan = Drawing(fit=True)
        with patch("shutil.get_terminal_size",
                   return_value=os.terminal_size((120, 40))):
            plan.fit_to(Maze(20, 15))
            drawn = plain(render(Maze(20, 15), plan)).split("\n")
        self.assertEqual(
            {len(line) for line in drawn},
            {drawing_size(20, 15, plan.cell_width, plan.frame)[0]})

    def test_rendering_fits_without_being_asked_first(self) -> None:
        """``render`` settles it too, for a caller that does not care."""
        with patch("shutil.get_terminal_size",
                   return_value=os.terminal_size((120, 40))):
            drawn = plain(render(Maze(20, 15), Drawing(fit=True)))
        self.assertEqual(len(drawn.split("\n")[0]),
                         drawing_size(20, 15, CELL_WIDTH, FRAME)[0])

    def test_no_room_at_any_width_raises(self) -> None:
        """Nothing fits, so there is no drawing and no width to give."""
        plan = Drawing(fit=True)
        with patch("shutil.get_terminal_size",
                   return_value=os.terminal_size((30, 10))):
            with self.assertRaises(TooSmall):
                plan.fit_to(Maze(20, 15))


if __name__ == "__main__":
    unittest.main()
