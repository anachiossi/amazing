"""Tests for the window renderer.

Run from the repository root::

    python3 -m unittest discover -s tests -t .

Nothing here opens a window. MLX is only reached for from inside
``MazeWindow``, so everything below — the arithmetic of the layout and
the drawing itself — is checked against a canvas backed by an ordinary
bytearray, which is all an MLX image is once it has been handed over.
"""

import unittest

from mazegen import Direction, Maze

from app.render.gui import (DOWN, ESCAPE, FOOT, HEAD, KEYS, LEFT, LINE, MARGIN,
                            MAX_CELL, MIN_CELL, RIGHT, STANDARD_SKIN, TAIL,
                            TAIL_LINES, UP, Canvas, Layout, Scene, TooSmall,
                            ascii_only, colour, draw, key_letter,
                            path_prefixes, write_line)

# A screen big enough that nothing has to be given up for it.
ROOMY = (3000, 2000)


class FakeMlx:
    """As much of MLX as a canvas uses: one image, held in memory.

    ``mlx_get_data_addr`` hands back the pixels of an image, the bits
    each takes, the length of a row and the order the bytes go in.
    Every one of those is answered here the way the real library
    answers it on an ordinary machine.
    """

    def __init__(self) -> None:
        self.stride = 0
        self.pixels = memoryview(bytearray())

    def mlx_new_image(self, mlx_ptr: object, width: int, height: int) -> str:
        self.stride = width * 4
        self.pixels = memoryview(bytearray(self.stride * height))
        return "image"

    def mlx_get_data_addr(self, image: str) -> tuple[memoryview, int, int,
                                                     int]:
        return self.pixels, 32, self.stride, 0


def canvas_of(width: int, height: int) -> Canvas:
    """A canvas of that size, drawing into memory."""
    return Canvas(FakeMlx(), None, width, height)


def pixel(canvas: Canvas, x: int, y: int) -> int:
    """The colour of one pixel, read back the way it was written."""
    start = y * canvas.stride + x * canvas.depth
    return int.from_bytes(canvas.pixels[start:start + canvas.depth],
                          canvas.order)


def drawn(maze: Maze, path: tuple[tuple[int, int], ...] = ()
          ) -> tuple[Canvas, Layout]:
    """Draw a maze into a canvas of its own, and hand both back."""
    layout = Layout.fit(maze, ROOMY)
    width, height = layout.window
    canvas = canvas_of(width, height)
    draw(canvas, maze, layout, STANDARD_SKIN, path)
    return canvas, layout


class ColourTest(unittest.TestCase):
    """A name becomes the number MLX draws with."""

    def test_colour_is_opaque(self) -> None:
        self.assertEqual(colour("snow") >> 24, 0xFF)

    def test_colour_carries_red_green_and_blue(self) -> None:
        # chambray is 135, 175, 215 in the palette rainbow shares.
        self.assertEqual(colour("chambray") & 0xFFFFFF, 0x87AFD7)

    def test_a_number_names_a_colour_too(self) -> None:
        self.assertEqual(colour(110), colour("chambray"))


class LayoutTest(unittest.TestCase):
    """Where the maze lands, in pixels."""

    def test_a_small_maze_gets_the_biggest_cell(self) -> None:
        self.assertEqual(Layout.fit(Maze(4, 4), ROOMY).cell, MAX_CELL)

    def test_a_large_maze_gets_a_smaller_cell(self) -> None:
        layout = Layout.fit(Maze(300, 200), ROOMY)
        self.assertLess(layout.cell, MAX_CELL)
        self.assertGreaterEqual(layout.cell, MIN_CELL)

    def test_a_maze_too_large_for_the_screen_is_refused(self) -> None:
        with self.assertRaises(TooSmall):
            Layout.fit(Maze(1000, 1000), (800, 600))

    def test_the_window_holds_the_whole_maze(self) -> None:
        maze = Maze(20, 15)
        layout = Layout.fit(maze, ROOMY)
        window_width, window_height = layout.window
        left, top = layout.corner(19, 14)
        self.assertLessEqual(left + layout.cell + MARGIN, window_width)
        self.assertEqual(top + layout.cell + TAIL, window_height)

    def test_the_tail_leaves_room_under_the_keys(self) -> None:
        # The last caption sits TAIL_LINES lines into the tail; FOOT
        # is what remains under it, so the keys are not drawn on the
        # window's bottom edge.
        self.assertEqual(TAIL, TAIL_LINES * LINE + FOOT)
        self.assertGreater(FOOT, 0)

    def test_cells_sit_side_by_side(self) -> None:
        layout = Layout.fit(Maze(5, 5), ROOMY)
        left, top = layout.corner(0, 0)
        self.assertEqual(layout.corner(1, 0), (left + layout.cell, top))
        self.assertEqual(layout.corner(0, 1), (left, top + layout.cell))

    def test_the_maze_starts_below_the_head(self) -> None:
        layout = Layout.fit(Maze(5, 5), ROOMY)
        self.assertEqual(layout.corner(0, 0)[1], HEAD)

    def test_the_centre_of_a_cell_is_inside_it(self) -> None:
        layout = Layout.fit(Maze(5, 5), ROOMY)
        left, top = layout.corner(2, 3)
        middle_x, middle_y = layout.centre(2, 3)
        self.assertTrue(left < middle_x < left + layout.cell)
        self.assertTrue(top < middle_y < top + layout.cell)


class CanvasTest(unittest.TestCase):
    """Rectangles, and what happens at the edges."""

    def test_fill_paints_every_pixel(self) -> None:
        canvas = canvas_of(4, 3)
        canvas.fill(colour("snow"))
        for x in range(4):
            for y in range(3):
                self.assertEqual(pixel(canvas, x, y), colour("snow"))

    def test_a_rectangle_paints_only_itself(self) -> None:
        canvas = canvas_of(8, 8)
        canvas.rect(2, 2, 3, 3, colour("madder"))
        self.assertEqual(pixel(canvas, 2, 2), colour("madder"))
        self.assertEqual(pixel(canvas, 4, 4), colour("madder"))
        self.assertEqual(pixel(canvas, 5, 4), 0)
        self.assertEqual(pixel(canvas, 4, 5), 0)

    def test_what_falls_off_the_left_is_cut_not_wrapped(self) -> None:
        # A row written past its end would show up at the start of the
        # next one, which is the mistake worth a test of its own.
        canvas = canvas_of(8, 8)
        canvas.rect(-3, 0, 5, 1, colour("madder"))
        self.assertEqual(pixel(canvas, 0, 0), colour("madder"))
        self.assertEqual(pixel(canvas, 1, 0), colour("madder"))
        self.assertEqual(pixel(canvas, 2, 0), 0)
        self.assertEqual(pixel(canvas, 7, 1), 0)

    def test_a_rectangle_entirely_outside_draws_nothing(self) -> None:
        canvas = canvas_of(4, 4)
        canvas.rect(10, 10, 5, 5, colour("madder"))
        self.assertEqual(bytes(canvas.pixels), bytes(4 * 4 * 4))


class DrawTest(unittest.TestCase):
    """The picture itself, read back pixel by pixel."""

    def test_a_walled_cell_has_floor_inside_and_walls_around(self) -> None:
        maze = Maze(1, 1)
        canvas, layout = drawn(maze)
        self.assertEqual(pixel(canvas, *layout.centre(0, 0)),
                         STANDARD_SKIN.floor)
        left, top = layout.corner(0, 0)
        middle = layout.cell // 2
        self.assertEqual(pixel(canvas, left + middle, top),
                         STANDARD_SKIN.wall)
        self.assertEqual(pixel(canvas, left, top + middle),
                         STANDARD_SKIN.wall)

    def test_an_open_side_is_floor_where_the_wall_would_be(self) -> None:
        maze = Maze(2, 1)
        maze.destroy_wall(0, 0, Direction.E)
        canvas, layout = drawn(maze)
        left, top = layout.corner(1, 0)
        self.assertEqual(pixel(canvas, left, top + layout.cell // 2),
                         STANDARD_SKIN.floor)

    def test_the_ends_are_drawn_where_the_maze_says(self) -> None:
        maze = Maze(3, 3, entry=(0, 0), exit=(2, 2))
        canvas, layout = drawn(maze)
        self.assertEqual(pixel(canvas, *layout.centre(0, 0)),
                         STANDARD_SKIN.entry)
        self.assertEqual(pixel(canvas, *layout.centre(2, 2)),
                         STANDARD_SKIN.exit)

    def test_the_42_is_drawn_in_its_own_colour(self) -> None:
        maze = Maze(3, 3)
        maze.set_frozen([(1, 1)])
        canvas, layout = drawn(maze)
        self.assertEqual(pixel(canvas, *layout.centre(1, 1)),
                         STANDARD_SKIN.forty_two)

    def test_a_path_is_a_yellow_trail_through_its_cells(self) -> None:
        maze = Maze(3, 1)
        maze.destroy_wall(0, 0, Direction.E)
        maze.destroy_wall(1, 0, Direction.E)
        canvas, layout = drawn(maze, ((0, 0), (1, 0), (2, 0)))
        self.assertEqual(STANDARD_SKIN.path, colour("yellow"))
        self.assertEqual(pixel(canvas, *layout.centre(1, 0)),
                         STANDARD_SKIN.path)
        # Neighbouring cells join: the opening where they meet is the
        # path, not a gap of floor between two tiles.
        left, top = layout.corner(1, 0)
        self.assertEqual(pixel(canvas, left, top + layout.cell // 2),
                         STANDARD_SKIN.path)

    def test_no_path_leaves_the_floor_alone(self) -> None:
        maze = Maze(3, 1)
        maze.destroy_wall(0, 0, Direction.E)
        canvas, layout = drawn(maze)
        self.assertEqual(pixel(canvas, *layout.centre(1, 0)),
                         STANDARD_SKIN.floor)

    def test_a_path_of_one_cell_is_still_drawn(self) -> None:
        maze = Maze(2, 1)
        canvas, layout = drawn(maze, ((0, 0),))
        self.assertEqual(pixel(canvas, *layout.centre(0, 0)),
                         STANDARD_SKIN.path)
        self.assertEqual(pixel(canvas, *layout.centre(1, 0)),
                         STANDARD_SKIN.floor)

    def test_walls_are_drawn_over_the_path(self) -> None:
        # The path is asked to cross a wall that stands. The wall wins:
        # a drawing that let a route through a wall would be a lie.
        maze = Maze(2, 1)
        canvas, layout = drawn(maze, ((0, 0), (1, 0)))
        left, top = layout.corner(1, 0)
        self.assertEqual(pixel(canvas, left, top + layout.cell // 2),
                         STANDARD_SKIN.wall)


class TextTest(unittest.TestCase):
    """Captions painted into the image."""

    def test_a_letter_is_painted_on_the_canvas(self) -> None:
        canvas = canvas_of(80, 20)
        canvas.fill(colour("cinder"))
        write_line(canvas, "P", 2, colour("snow"))
        painted = 0
        for y in range(canvas.height):
            for x in range(canvas.width):
                if pixel(canvas, x, y) == colour("snow"):
                    painted += 1
        self.assertGreater(painted, 0)

    def test_plain_text_is_left_alone(self) -> None:
        self.assertEqual(ascii_only("20x15 seed 42"), "20x15 seed 42")

    def test_the_characters_a_caption_carries_have_a_plain_twin(self
                                                                ) -> None:
        self.assertEqual(ascii_only("20x15 · braided — seed"),
                         "20x15 - braided - seed")

    def test_anything_else_becomes_a_question_mark(self) -> None:
        self.assertEqual(ascii_only("ဩ"), "?")

    def test_the_keys_are_three_lines(self) -> None:
        self.assertEqual(len(KEYS), 3)
        self.assertIn("R generate", KEYS[0])
        self.assertIn("P path", KEYS[0])
        self.assertIn("Q quit", KEYS[0])
        self.assertNotIn("arrows", KEYS[0])
        self.assertIn("C wall colour", KEYS[1])
        self.assertIn("F 42 colour", KEYS[1])
        self.assertIn("G gen. alg.", KEYS[2])
        self.assertIn("A gen. anim.", KEYS[2])
        self.assertIn("S solver alg.", KEYS[2])
        self.assertIn("V solver anim.", KEYS[2])

    def test_the_keys_are_letters_the_font_has(self) -> None:
        # A missing glyph is drawn as "?"; that is how "quit" used to
        # read as "?uit".
        from app.render.gui import _FONT_5X7
        missing = sorted({letter for line in KEYS for letter in line
                          if letter not in _FONT_5X7})
        self.assertEqual(missing, [])

    def test_q_is_not_drawn_as_a_question_mark(self) -> None:
        from app.render.gui import _FONT_5X7
        self.assertNotEqual(_FONT_5X7["Q"], _FONT_5X7["?"])
        self.assertNotEqual(_FONT_5X7["q"], _FONT_5X7["?"])

    def test_the_title_is_letters_the_font_has(self) -> None:
        # A-MAZE-ING used to paint as A-MA??-IN?: Z, E and G had no
        # glyphs, and a missing glyph is "?".
        from app.render.gui import _FONT_5X7
        missing = sorted({letter for letter in "A-MAZE-ING"
                          if letter not in _FONT_5X7})
        self.assertEqual(missing, [])

    def test_the_alphabet_is_in_the_font(self) -> None:
        from app.render.gui import _FONT_5X7
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        missing = [letter for letter in letters if letter not in _FONT_5X7]
        self.assertEqual(missing, [])

    def test_a_colon_is_in_the_font(self) -> None:
        from app.render.gui import _FONT_5X7
        self.assertIn(":", _FONT_5X7)
        self.assertNotEqual(_FONT_5X7[":"], _FONT_5X7["?"])


class KeyLetterTest(unittest.TestCase):
    """MLX keysyms become the letters the window answers."""

    def test_key_letter_reads_printable_keys_escape_and_arrows(self) -> None:
        self.assertEqual(key_letter(ord("p")), "p")
        self.assertEqual(key_letter(ord("P")), "p")
        self.assertEqual(key_letter(ESCAPE), "\x1b")
        self.assertEqual(key_letter(LEFT), "left")
        self.assertEqual(key_letter(UP), "up")
        self.assertEqual(key_letter(RIGHT), "right")
        self.assertEqual(key_letter(DOWN), "down")
        self.assertEqual(key_letter(65505), "")


class PathPrefixesTest(unittest.TestCase):
    """The solver animation grows the route a cell at a time."""

    def test_the_route_starts_empty_and_ends_whole(self) -> None:
        path = ((0, 0), (1, 0), (1, 1))
        frames = list(path_prefixes(path))
        self.assertEqual(frames[0], ())
        self.assertEqual(frames[-1], path)
        self.assertEqual(len(frames), len(path) + 1)


class SceneTest(unittest.TestCase):
    """The maze, the route and the words travel together."""

    def test_a_scene_needs_nothing_but_a_maze(self) -> None:
        scene = Scene(Maze(2, 2))
        self.assertEqual(scene.path, ())
        self.assertEqual(scene.title, "")
        self.assertEqual(scene.message, ())


if __name__ == "__main__":
    unittest.main()
