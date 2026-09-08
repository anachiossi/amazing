"""Tests for the captions the program writes under a maze."""

import unittest

from mazegen import Direction, Maze, MazeConfig, MazeGenerator, MazeSolver

from a_maze_ing import describes, message_for, moved_entry, next_named
from app.render.terminal import Drawing


def config() -> MazeConfig:
    return MazeConfig(20, 15, (0, 0), (19, 14))


class DescribesTest(unittest.TestCase):
    """The lines under the maze name the generator, the solver, the size."""

    def test_the_captions_name_generation_solver_and_resolution(self) -> None:
        lines = describes(config(), "kruskal", "bfs")
        self.assertEqual(lines, [
            "generation: kruskal",
            "solver: bfs",
            "resolution: 20x15",
        ])

    def test_the_captions_do_not_name_the_seed_or_the_shape(self) -> None:
        text = " ".join(describes(config(), "kruskal", "bfs"))
        self.assertNotIn("seed", text)
        self.assertNotIn("braided", text)
        self.assertNotIn("perfect", text)
        self.assertNotIn("generated with", text)

    def test_the_captions_are_letters_the_font_has(self) -> None:
        from app.render.gui import _FONT_5X7
        missing = sorted({letter
                          for line in describes(config(), "kruskal", "bfs")
                          for letter in line
                          if letter not in _FONT_5X7})
        self.assertEqual(missing, [])

    def test_the_terminal_keeps_the_same_captions(self) -> None:
        drawing = Drawing()
        drawing.cell_width = 3
        lines = message_for(drawing, config(), "kruskal", "bfs")
        self.assertEqual(lines[:3], describes(config(), "kruskal", "bfs"))


class NextNamedTest(unittest.TestCase):
    """G and S walk the registered algorithms in name order."""

    def test_the_next_generator_wraps_around(self) -> None:
        names = sorted(MazeGenerator.algorithms)
        self.assertGreaterEqual(len(names), 2)
        self.assertEqual(next_named(MazeGenerator.algorithms, names[-1]),
                         names[0])
        self.assertEqual(next_named(MazeGenerator.algorithms, names[0]),
                         names[1])

    def test_the_next_solver_stays_in_the_registry(self) -> None:
        nxt = next_named(MazeSolver.algorithms, "bfs")
        self.assertIn(nxt, MazeSolver.algorithms)

    def test_an_unknown_name_starts_at_the_first(self) -> None:
        names = sorted(MazeGenerator.algorithms)
        self.assertEqual(next_named(MazeGenerator.algorithms, "nope"),
                         names[0])


class MovedEntryTest(unittest.TestCase):
    """The arrows step the entry one cell, and stop where they must."""

    def test_the_entry_steps_through_an_opening(self) -> None:
        maze = Maze(3, 3, entry=(1, 1), exit=(2, 2))
        for side in (Direction.N, Direction.E, Direction.S, Direction.W):
            maze.destroy_wall(1, 1, side)
        self.assertEqual(moved_entry(maze, "left"), (0, 1))
        self.assertEqual(moved_entry(maze, "right"), (2, 1))
        self.assertEqual(moved_entry(maze, "up"), (1, 0))
        self.assertEqual(moved_entry(maze, "down"), (1, 2))

    def test_a_wall_stops_the_entry(self) -> None:
        maze = Maze(3, 3, entry=(1, 1), exit=(2, 2))
        maze.destroy_wall(1, 1, Direction.E)
        self.assertEqual(moved_entry(maze, "right"), (2, 1))
        self.assertIsNone(moved_entry(maze, "left"))
        self.assertIsNone(moved_entry(maze, "up"))
        self.assertIsNone(moved_entry(maze, "down"))

    def test_the_entry_stops_at_the_edge(self) -> None:
        maze = Maze(2, 2, entry=(0, 0), exit=(1, 1))
        self.assertIsNone(moved_entry(maze, "left"))
        self.assertIsNone(moved_entry(maze, "up"))

    def test_the_entry_does_not_land_on_the_exit(self) -> None:
        maze = Maze(3, 1, entry=(0, 0), exit=(1, 0))
        maze.destroy_wall(0, 0, Direction.E)
        self.assertIsNone(moved_entry(maze, "right"))

    def test_the_entry_does_not_land_on_the_42(self) -> None:
        maze = Maze(3, 3, entry=(1, 1), exit=(2, 2))
        maze.set_frozen(((1, 0),))
        maze.destroy_wall(1, 1, Direction.N)
        maze.destroy_wall(1, 1, Direction.W)
        self.assertIsNone(moved_entry(maze, "up"))
        self.assertEqual(moved_entry(maze, "left"), (0, 1))

    def test_a_key_that_is_not_an_arrow_moves_nothing(self) -> None:
        maze = Maze(3, 3, entry=(1, 1), exit=(2, 2))
        self.assertIsNone(moved_entry(maze, "r"))
