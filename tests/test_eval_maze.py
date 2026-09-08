"""The evaluation sheet's maze requirements, one test per bullet.

``subject/eval_amazing.pdf`` asks a single Yes/No over the nine bullets
of "Maze Generator module / Maze generation".  One Yes/No is a poor
thing to debug on the morning of a defence, so every bullet gets its
own test here and is named after it.  The bullets, in the sheet's own
order:

1. a randomly generated maze                      -> RandomnessTest
2. relevant behaviour on inconsistent parameters   -> InconsistentTest
3. all cells reachable, except the "42"            -> ReachableTest
4. walls all around the maze                       -> BorderTest
5. no 3x3 or larger open zone without walls        -> OpenZoneTest
6. the "42" pattern is in the maze                 -> FortyTwoTest
7. PERFECT=True  -> one path, no loops             -> PerfectTest
8. PERFECT=False -> a Pac-Man board                -> BraidedTest
9. the same seed gives the same maze               -> RandomnessTest

The other test files ask whether a piece works; this one asks whether
the project passes.  The overlap with test_kruskal.py and
test_backtracker.py is deliberate: those two questions want to fail
separately, so that a broken algorithm and a broken promise do not
look the same in the output.

Every bullet is asked of both algorithms and of both modes, because
the evaluator may set either in the configuration file.
"""

import unittest
from functools import lru_cache

from mazegen import (Cell, Cells, Direction, Maze, MazeConfig,
                     MazeGenerator, MazeSolver, forty_two)

# The mazes every bullet is asked over. The first size is the smallest
# one the "42" fits in, the second is what config.txt ships with, and
# the third is large enough for the braiding to have room to go wrong.
# Four seeds, because a braided maze is expensive to build and these
# are generated once and shared by the whole file.
SIZES = ((11, 9), (18, 9), (20, 15))
SEEDS = (0, 1, 2, 3)
ALGORITHMS = ("kruskal", "backtracker")


@lru_cache(maxsize=None)
def maze_for(width: int, height: int, seed: int, perfect: bool,
             algorithm: str = "kruskal") -> Maze:
    """A finished maze, built once and remembered.

    Entry and exit are the two opposite corners, which is what
    config.txt asks for and what keeps them clear of the "42".
    """
    config = MazeConfig(width, height, (0, 0), (width - 1, height - 1),
                        perfect=perfect, seed=seed,
                        gen_algorithm=algorithm)
    return MazeGenerator.from_config(config).generate()


def every_maze(perfect: bool) -> list[tuple[str, int, int, int, Maze]]:
    """Every maze of that mode, each with what it was built from."""
    return [(algorithm, width, height, seed,
             maze_for(width, height, seed, perfect, algorithm))
            for algorithm in ALGORITHMS
            for width, height in SIZES
            for seed in SEEDS]


def region(maze: Maze) -> Cells:
    """Every cell reachable from the entry: the playable board."""
    entry = maze.get_entry()
    if entry is None:
        raise ValueError("the maze has no entry to search from")
    return maze.region_of(*entry)


def playable(maze: Maze) -> Cells:
    """Every cell but the "42": what a player is meant to reach."""
    glyph = maze.get_frozen()
    return frozenset((col, row)
                     for col in range(maze.width)
                     for row in range(maze.height)
                     if (col, row) not in glyph)


def loops(maze: Maze) -> int:
    """Independent routes through the playable region.

    ``edges - nodes + 1``, which is what the analyzer counts: zero for
    a tree, and one more for every passage that closes a circuit.  The
    sheet's "at least two independent routes" is this number.
    """
    inside = region(maze)
    joined = [edge for edge in maze.open_passages() if edge <= inside]
    return len(joined) - len(inside) + 1


def real_dead_ends(maze: Maze) -> list[Cell]:
    """The dead-ends the analyzer holds against a playable board.

    A cell with a single way out is *real* when one of its standing
    walls could be opened towards an ordinary cell, and *enclosed* —
    which the analyzer tolerates — when every one of them faces the
    "42" or the outer border.
    """
    found: list[Cell] = []
    for col, row in sorted(region(maze)):
        if len(maze.passages(col, row)) != 1:
            continue
        if any(maze.wall_count(*maze.across(col, row, side)) != 4
               for side in maze.closed_walls(col, row)):
            found.append((col, row))
    return found


def centre_cells(width: int, height: int) -> Cells:
    """The cell or cells at the middle, the way the analyzer picks them.

    An odd side has one middle cell; an even side has no cell dead in
    the middle, so either of the two straddling it will do.
    """
    cols = {width // 2} if width % 2 else {width // 2 - 1, width // 2}
    rows = {height // 2} if height % 2 else {height // 2 - 1, height // 2}
    return frozenset((col, row) for col in cols for row in rows)


def walled_inside(maze: Maze, col: int, row: int, size: int) -> bool:
    """Whether any wall still stands between the cells of that block."""
    for step_col in range(size):
        for step_row in range(size):
            here, there = col + step_col, row + step_row
            if step_col < size - 1 and maze.get_wall(here, there,
                                                     Direction.E):
                return True
            if step_row < size - 1 and maze.get_wall(here, there,
                                                     Direction.S):
                return True
    return False


def open_rooms(maze: Maze, size: int = 3) -> list[Cell]:
    """The top-left corner of every open zone that big.

    "Open zone" is read the way the sheet draws it: a block of cells a
    player could cross freely because not one of the walls *between*
    them stands.  The walls around the outside of the block are not
    looked at — those are what would make it a room rather than a
    field.

    A 4x4 open zone contains a 3x3 one, so a maze with no 3x3 room has
    no larger one either, and only this size has to be asked for.
    """
    return [(col, row)
            for col in range(maze.width - size + 1)
            for row in range(maze.height - size + 1)
            if not walled_inside(maze, col, row, size)]


class RandomnessTest(unittest.TestCase):
    """Bullets 1 and 9: random, and repeatable when told a seed."""

    def walls_of(self, maze: Maze) -> list[int]:
        return [int(maze.grid[col][row])
                for col in range(maze.width)
                for row in range(maze.height)]

    def test_two_mazes_with_no_seed_differ(self) -> None:
        """Bullet 1: the maze is generated at random."""
        config = MazeConfig(18, 9, (0, 0), (17, 8))
        first = MazeGenerator.from_config(config).generate()
        second = MazeGenerator.from_config(config).generate()
        self.assertNotEqual(self.walls_of(first), self.walls_of(second))

    def test_the_same_seed_gives_the_same_maze(self) -> None:
        """Bullet 9: replicable from the seed in the config file."""
        for algorithm in ALGORITHMS:
            with self.subTest(algorithm=algorithm):
                first = maze_for(18, 9, 7, False, algorithm)
                second = MazeGenerator.from_config(
                    MazeConfig(18, 9, (0, 0), (17, 8), perfect=False,
                               seed=7, gen_algorithm=algorithm)).generate()
                self.assertEqual(self.walls_of(first),
                                 self.walls_of(second))

    def test_a_different_seed_gives_a_different_maze(self) -> None:
        """Otherwise the seed would not be doing anything."""
        for algorithm in ALGORITHMS:
            with self.subTest(algorithm=algorithm):
                self.assertNotEqual(
                    self.walls_of(maze_for(18, 9, 1, True, algorithm)),
                    self.walls_of(maze_for(18, 9, 2, True, algorithm)))


class InconsistentTest(unittest.TestCase):
    """Bullet 2: a relevant behaviour when the parameters cannot hold.

    Relevant means refused where the mistake is made, with a message
    naming it — never a traceback, which the sheet grades 0.  The same
    values coming through the configuration file are checked end to
    end in test_eval_cli.py.
    """

    def test_a_negative_or_empty_size_is_refused(self) -> None:
        for width, height in ((-5, 9), (18, -1), (0, 9), (18, 0)):
            with self.subTest(size=(width, height)):
                with self.assertRaises(ValueError):
                    MazeConfig(width, height, (0, 0), (1, 1))

    def test_an_end_outside_the_maze_is_refused(self) -> None:
        for entry, exit_cell in (((-1, 0), (17, 8)), ((0, 0), (18, 8)),
                                 ((0, 9), (17, 8)), ((0, 0), (17, -2))):
            with self.subTest(entry=entry, exit=exit_cell):
                with self.assertRaises(ValueError):
                    MazeConfig(18, 9, entry, exit_cell)

    def test_the_message_says_which_end_and_which_maze(self) -> None:
        with self.assertRaises(ValueError) as raised:
            MazeConfig(18, 9, (0, 0), (99, 99))
        self.assertIn("exit", str(raised.exception))
        self.assertIn("18x9", str(raised.exception))

    def test_an_unknown_algorithm_names_the_ones_there_are(self) -> None:
        config = MazeConfig(18, 9, (0, 0), (17, 8),
                            gen_algorithm="no-such-algorithm")
        with self.assertRaises(ValueError) as raised:
            MazeGenerator.from_config(config)
        for algorithm in ALGORITHMS:
            self.assertIn(algorithm, str(raised.exception))

    def test_an_entry_sealed_inside_the_42_does_not_crash(self) -> None:
        """The one inconsistency the program tolerates rather than refuses.

        The "42" is closed before the maze is carved, so an entry that
        lands on one of its cells is walled in and the solver finds no
        way out.  Nothing raises and nothing loops, which is what the
        sheet's fatal criterion asks for; the maze simply has no path
        to show.
        """
        entry = min(forty_two.cells(20, 15))
        config = MazeConfig(20, 15, entry, (19, 14), perfect=False, seed=1)
        maze = MazeGenerator.from_config(config).generate()
        self.assertEqual(maze.wall_count(*entry), 4)
        self.assertEqual(list(MazeSolver.from_config(config).solve(maze)), [])


class ReachableTest(unittest.TestCase):
    """Bullet 3: every cell reachable, except the "42"'s."""

    def test_every_cell_but_the_42_is_reachable(self) -> None:
        for perfect in (True, False):
            for algorithm, width, height, seed, maze in every_maze(perfect):
                with self.subTest(algorithm=algorithm, perfect=perfect,
                                  size=(width, height), seed=seed):
                    self.assertEqual(region(maze), playable(maze))

    def test_no_corridor_is_left_stranded(self) -> None:
        """The analyzer's rule, said the way the analyzer says it.

        A cell outside the playable region that is not one of the
        fully closed "42" cells is a corridor nobody can reach, and it
        makes the analyzer report the board unwinnable.
        """
        for perfect in (True, False):
            for algorithm, width, height, seed, maze in every_maze(perfect):
                with self.subTest(algorithm=algorithm, perfect=perfect,
                                  size=(width, height), seed=seed):
                    inside = region(maze)
                    stranded = [(col, row)
                                for col in range(width)
                                for row in range(height)
                                if (col, row) not in inside
                                and maze.wall_count(col, row) != 4]
                    self.assertEqual(stranded, [])


class BorderTest(unittest.TestCase):
    """Bullet 4: walls all around the maze."""

    def test_the_border_is_closed_all_the_way_round(self) -> None:
        for perfect in (True, False):
            for algorithm, width, height, seed, maze in every_maze(perfect):
                with self.subTest(algorithm=algorithm, perfect=perfect,
                                  size=(width, height), seed=seed):
                    for col in range(width):
                        self.assertTrue(maze.get_wall(col, 0, Direction.N))
                        self.assertTrue(
                            maze.get_wall(col, height - 1, Direction.S))
                    for row in range(height):
                        self.assertTrue(maze.get_wall(0, row, Direction.W))
                        self.assertTrue(
                            maze.get_wall(width - 1, row, Direction.E))


class OpenZoneTest(unittest.TestCase):
    """Bullet 5: no 3x3 or larger open zone without walls.

    Nothing in the generator forbids one.  A perfect maze cannot hold
    one — a tree has no room for the twelve passages a 3x3 room needs
    — but braiding and loosening both open walls after the fact, and
    they do not look at what they are opening into.
    """

    def test_no_3x3_block_is_free_of_walls(self) -> None:
        for perfect in (True, False):
            for algorithm, width, height, seed, maze in every_maze(perfect):
                with self.subTest(algorithm=algorithm, perfect=perfect,
                                  size=(width, height), seed=seed):
                    self.assertEqual(open_rooms(maze), [])

    def test_the_20x15_braided_maze_of_seed_3(self) -> None:
        """The case the sweep above first turned up, pinned on its own.

        Kept apart from the sweep so that it keeps being asked even if
        the sizes and seeds up there are ever changed.
        """
        maze = maze_for(20, 15, 3, False, "kruskal")
        self.assertEqual(open_rooms(maze), [])


class FortyTwoTest(unittest.TestCase):
    """Bullet 6: the "42" is in the maze, or the size does not allow it."""

    def test_the_pattern_is_there_and_stays_closed(self) -> None:
        for perfect in (True, False):
            for algorithm, width, height, seed, maze in every_maze(perfect):
                with self.subTest(algorithm=algorithm, perfect=perfect,
                                  size=(width, height), seed=seed):
                    expected = forty_two.cells(width, height)
                    self.assertEqual(maze.get_frozen(), expected)
                    for col, row in expected:
                        self.assertEqual(maze.wall_count(col, row), 4)

    def test_the_pattern_keeps_off_the_corners_and_the_middle(self) -> None:
        """Bullet 8 leans on this: a board needs both as corridors."""
        for width, height in SIZES:
            with self.subTest(size=(width, height)):
                glyph = forty_two.cells(width, height)
                corners = {(0, 0), (width - 1, 0),
                           (0, height - 1), (width - 1, height - 1)}
                self.assertEqual(glyph & corners, frozenset())
                self.assertNotEqual(centre_cells(width, height) - glyph,
                                    frozenset())

    def test_a_maze_with_no_room_goes_without_the_pattern(self) -> None:
        """Below the minimum the maze is carved whole, and says nothing.

        The sheet allows the missing pattern at a size that cannot hold
        it, provided the program says so on the terminal.  That the
        maze itself is well formed is asked here; that the program says
        anything is asked in test_eval_cli.py.
        """
        maze = maze_for(forty_two.MIN_WIDTH - 1, forty_two.MIN_HEIGHT,
                        1, False)
        self.assertEqual(maze.get_frozen(), frozenset())
        self.assertEqual(region(maze), playable(maze))


class PerfectTest(unittest.TestCase):
    """Bullet 7: PERFECT=True is exactly one path, and no loops."""

    def test_the_playable_region_is_a_tree(self) -> None:
        """One path between any two cells is what having no loop means."""
        for algorithm, width, height, seed, maze in every_maze(True):
            with self.subTest(algorithm=algorithm, size=(width, height),
                              seed=seed):
                self.assertEqual(loops(maze), 0)

    def test_exactly_one_route_from_entry_to_exit(self) -> None:
        """Said the other way round: every step of it is a choke point.

        If any passage on the route could be closed with the exit
        still reachable, there would be a way round it, and so a
        second route.
        """
        for algorithm, width, height, seed, maze in every_maze(True):
            with self.subTest(algorithm=algorithm, size=(width, height),
                              seed=seed):
                config = MazeConfig(width, height, (0, 0),
                                    (width - 1, height - 1), perfect=True,
                                    seed=seed, gen_algorithm=algorithm)
                route = MazeSolver.from_config(config).solve(maze)
                self.assertGreater(len(route), 1)
                for before, after in zip(route, route[1:]):
                    banned = frozenset((before, after))
                    self.assertNotIn(
                        (width - 1, height - 1),
                        maze.region_of(0, 0, banned=banned))


class BraidedTest(unittest.TestCase):
    """Bullet 8: PERFECT=False is a board a Pac-Man could be played on.

    The sheet spells out what that means, and the analyzer measures
    each of them: full connectivity, the four corners and the centre
    open, at least two independent routes, and few enough dead-ends.
    """

    def test_the_four_corners_are_open_corridors(self) -> None:
        for algorithm, width, height, seed, maze in every_maze(False):
            with self.subTest(algorithm=algorithm, size=(width, height),
                              seed=seed):
                inside = region(maze)
                for corner in ((0, 0), (width - 1, 0),
                               (0, height - 1), (width - 1, height - 1)):
                    self.assertIn(corner, inside)

    def test_the_centre_is_an_open_corridor(self) -> None:
        """Where the player starts, so it cannot be part of the "42"."""
        for algorithm, width, height, seed, maze in every_maze(False):
            with self.subTest(algorithm=algorithm, size=(width, height),
                              seed=seed):
                self.assertNotEqual(
                    centre_cells(width, height) & region(maze), frozenset())

    def test_there_are_at_least_two_independent_routes(self) -> None:
        """The analyzer's --min-loops, which defaults to 2."""
        for algorithm, width, height, seed, maze in every_maze(False):
            with self.subTest(algorithm=algorithm, size=(width, height),
                              seed=seed):
                self.assertGreaterEqual(loops(maze), 2)

    def test_no_single_passage_cuts_the_exit_off(self) -> None:
        """Two routes across the board, not two loops off in a corner.

        A count of loops does not say where they are: they could all
        sit to one side while every way to the exit still runs through
        one shared passage.  This asks the stronger question the
        config file promises.

        Every passage is tried in turn against a fresh search, which
        is the slowest thing in this file, so it is asked of the two
        smaller sizes only.  What it asks does not depend on the size.
        """
        for algorithm, width, height, seed, maze in every_maze(False):
            if (width, height) not in SIZES[:2]:
                continue
            with self.subTest(algorithm=algorithm, size=(width, height),
                              seed=seed):
                for edge in maze.open_passages():
                    self.assertIn((width - 1, height - 1),
                                  maze.region_of(0, 0, banned=edge))

    def test_few_enough_dead_ends(self) -> None:
        """The analyzer tolerates two; a braided board should have none.

        Zero is what earns the sheet's braided bonus, so it is what is
        asked for here rather than the tolerance.
        """
        for algorithm, width, height, seed, maze in every_maze(False):
            with self.subTest(algorithm=algorithm, size=(width, height),
                              seed=seed):
                self.assertEqual(real_dead_ends(maze), [])


if __name__ == "__main__":
    unittest.main()
