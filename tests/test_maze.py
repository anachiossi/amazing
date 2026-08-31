"""Tests for Maze and Direction.

Run from the repository root::

    python3 -m unittest discover -s tests -t .
"""

import random
import unittest
from itertools import product

from mazegen import Direction, Maze
from mazegen.maze import ALL_WALLS

SIDES = (Direction.N, Direction.E, Direction.S, Direction.W)


class MazeTest(unittest.TestCase):
    """Common helpers for the cases below."""

    def open_maze(self, width: int, height: int) -> Maze:
        """Return a maze whose every wall is down.

        Building starts from a closed grid, so a test that wants to
        watch a wall appear needs the opposite starting point.
        """
        maze = Maze(width, height)
        for col, row in product(range(width), range(height)):
            maze.grid[col][row] = Direction(0)
        return maze

    def snapshot(self, maze: Maze) -> list[list[int]]:
        """Copy the grid as plain numbers, to compare it later."""
        return [[int(cell) for cell in column] for column in maze.grid]

    def cells(self, maze: Maze) -> list[tuple[int, int]]:
        """List every cell of the maze."""
        width, height = maze.get_dim()
        return list(product(range(width), range(height)))

    def assert_coherent(self, maze: Maze) -> None:
        """Assert both sides of every wall agree, as the subject asks."""
        for col, row in self.cells(maze):
            for side in SIDES:
                step_col, step_row = side.step()
                other_col, other_row = col + step_col, row + step_row
                if not maze._is_inside(other_col, other_row):
                    continue
                self.assertEqual(
                    maze.get_wall(col, row, side),
                    maze.get_wall(other_col, other_row, side.opposite()),
                    f"cell ({col}, {row}) and its {side.name} neighbour "
                    f"disagree about the wall between them",
                )

    def assert_border_closed(self, maze: Maze) -> None:
        """Assert the external border is still walled all around."""
        for col, row in self.cells(maze):
            for side in SIDES:
                step_col, step_row = side.step()
                if maze._is_inside(col + step_col, row + step_row):
                    continue
                self.assertTrue(
                    maze.get_wall(col, row, side),
                    f"the {side.name} border of ({col}, {row}) is open",
                )


class TestDirection(MazeTest):
    """The encoding the subject imposes."""

    def test_bit_of_each_side(self) -> None:
        self.assertEqual((int(Direction.N), int(Direction.E),
                          int(Direction.S), int(Direction.W)), (1, 2, 4, 8))

    def test_all_walls_is_fifteen(self) -> None:
        self.assertEqual(int(ALL_WALLS), 15)

    def test_sides_combine(self) -> None:
        self.assertEqual(int(Direction.N | Direction.W), 9)

    def test_opposite(self) -> None:
        self.assertEqual(Direction.N.opposite(), Direction.S)
        self.assertEqual(Direction.E.opposite(), Direction.W)
        self.assertEqual(Direction.S.opposite(), Direction.N)
        self.assertEqual(Direction.W.opposite(), Direction.E)

    def test_opposite_twice_returns_the_same_side(self) -> None:
        for side in SIDES:
            self.assertEqual(side.opposite().opposite(), side)

    def test_step(self) -> None:
        """row grows downwards, so going north subtracts one."""
        self.assertEqual(Direction.N.step(), (0, -1))
        self.assertEqual(Direction.E.step(), (1, 0))
        self.assertEqual(Direction.S.step(), (0, 1))
        self.assertEqual(Direction.W.step(), (-1, 0))

    def test_step_of_opposite_cancels_out(self) -> None:
        for side in SIDES:
            col, row = side.step()
            other_col, other_row = side.opposite().step()
            self.assertEqual((col + other_col, row + other_row), (0, 0))

    def test_opposite_refuses_several_sides(self) -> None:
        with self.assertRaises(KeyError):
            (Direction.N | Direction.E).opposite()

    def test_step_refuses_several_sides(self) -> None:
        with self.assertRaises(KeyError):
            (Direction.N | Direction.E).step()


class TestConstruction(MazeTest):
    """A new maze is a solid block of closed cells."""

    def test_grid_is_columns_of_cells(self) -> None:
        """grid[col][row]: 4 columns of 3 cells, not the other way."""
        maze = Maze(4, 3)
        self.assertEqual(len(maze.grid), 4)
        for column in maze.grid:
            self.assertEqual(len(column), 3)

    def test_columns_are_independent(self) -> None:
        """Writing one cell must not show up in the other columns."""
        maze = Maze(3, 3)
        maze.grid[0][0] = Direction(0)
        self.assertEqual(int(maze.grid[1][0]), 15)
        self.assertEqual(int(maze.grid[2][0]), 15)

    def test_every_cell_starts_closed(self) -> None:
        maze = Maze(4, 3)
        for col, row in self.cells(maze):
            self.assertTrue(maze.no_access(col, row))

    def test_get_dim(self) -> None:
        self.assertEqual(Maze(20, 15).get_dim(), (20, 15))

    def test_smallest_maze(self) -> None:
        maze = Maze(1, 1)
        self.assertEqual(maze.get_dim(), (1, 1))
        self.assertTrue(maze.no_access(0, 0))

    def test_a_maze_needs_a_cell(self) -> None:
        for width, height in ((0, 5), (5, 0), (-1, 5), (0, 0)):
            with self.assertRaises(ValueError):
                Maze(width, height)

    def test_a_fresh_maze_is_coherent(self) -> None:
        self.assert_coherent(Maze(5, 4))
        self.assert_border_closed(Maze(5, 4))


class TestBounds(MazeTest):
    """Every method refuses a cell outside the grid."""

    def setUp(self) -> None:
        self.maze = Maze(3, 2)

    def test_get_wall(self) -> None:
        with self.assertRaises(IndexError):
            self.maze.get_wall(3, 0, Direction.N)

    def test_no_access(self) -> None:
        with self.assertRaises(IndexError):
            self.maze.no_access(0, 2)

    def test_build_wall(self) -> None:
        with self.assertRaises(IndexError):
            self.maze.build_wall(9, 9, Direction.N)

    def test_destroy_wall(self) -> None:
        with self.assertRaises(IndexError):
            self.maze.destroy_wall(9, 9, Direction.N)

    def test_adjacent_points(self) -> None:
        with self.assertRaises(IndexError):
            self.maze.adjacent_points(3, 0)

    def test_neighbours_points(self) -> None:
        with self.assertRaises(IndexError):
            self.maze.neighbours_points(0, 2)

    def test_negative_coordinates_are_refused(self) -> None:
        """Python would read the last column instead of failing."""
        for col, row in ((-1, 0), (0, -1)):
            with self.assertRaises(IndexError):
                self.maze.get_wall(col, row, Direction.N)

    def test_the_message_names_the_cell_and_the_size(self) -> None:
        with self.assertRaises(IndexError) as caught:
            self.maze.get_wall(3, 0, Direction.N)
        self.assertIn("(3, 0)", str(caught.exception))
        self.assertIn("3x2", str(caught.exception))


class TestGetWall(MazeTest):
    """Reading a single side of a cell."""

    def test_a_fresh_cell_is_closed_on_every_side(self) -> None:
        maze = Maze(3, 3)
        for side in SIDES:
            self.assertTrue(maze.get_wall(1, 1, side))

    def test_reads_the_side_it_is_asked_for(self) -> None:
        maze = self.open_maze(3, 3)
        maze.grid[1][1] = Direction.N | Direction.W
        self.assertTrue(maze.get_wall(1, 1, Direction.N))
        self.assertTrue(maze.get_wall(1, 1, Direction.W))
        self.assertFalse(maze.get_wall(1, 1, Direction.E))
        self.assertFalse(maze.get_wall(1, 1, Direction.S))

    def test_returns_a_bool_not_a_direction(self) -> None:
        self.assertIsInstance(Maze(3, 3).get_wall(1, 1, Direction.N), bool)


class TestNoAccess(MazeTest):
    """A cell closed by all four walls."""

    def test_true_when_every_wall_stands(self) -> None:
        self.assertTrue(Maze(3, 3).no_access(1, 1))

    def test_false_as_soon_as_one_wall_is_gone(self) -> None:
        maze = Maze(3, 3)
        maze.destroy_wall(1, 1, Direction.N)
        self.assertFalse(maze.no_access(1, 1))

    def test_false_on_an_open_cell(self) -> None:
        self.assertFalse(self.open_maze(3, 3).no_access(1, 1))

    def test_agrees_with_the_four_walls(self) -> None:
        maze = Maze(4, 4)
        maze.destroy_wall(2, 2, Direction.N)
        for col, row in self.cells(maze):
            self.assertEqual(
                maze.no_access(col, row),
                all(maze.get_wall(col, row, side) for side in SIDES),
            )


class TestBuildWall(MazeTest):
    """Building keeps both sides of a wall in step."""

    def test_sets_the_side_asked_for(self) -> None:
        maze = self.open_maze(3, 3)
        maze.build_wall(1, 1, Direction.N)
        self.assertEqual(int(maze.grid[1][1]), int(Direction.N))

    def test_sets_the_opposite_side_of_the_neighbour(self) -> None:
        maze = self.open_maze(3, 3)
        maze.build_wall(1, 1, Direction.N)
        self.assertEqual(int(maze.grid[1][0]), int(Direction.S))

    def test_leaves_the_other_cells_alone(self) -> None:
        maze = self.open_maze(3, 3)
        maze.build_wall(1, 1, Direction.N)
        self.assertEqual(int(maze.grid[0][0]), 0)
        self.assertEqual(int(maze.grid[2][2]), 0)

    def test_on_the_border_touches_only_the_cell(self) -> None:
        """There is no cell north of row 0, and it must not crash."""
        maze = self.open_maze(3, 3)
        maze.build_wall(0, 0, Direction.N)
        self.assertTrue(maze.get_wall(0, 0, Direction.N))

    def test_several_sides_at_once(self) -> None:
        maze = self.open_maze(3, 3)
        maze.build_wall(1, 1, ALL_WALLS)
        self.assertTrue(maze.no_access(1, 1))
        self.assertTrue(maze.get_wall(1, 0, Direction.S))
        self.assertTrue(maze.get_wall(2, 1, Direction.W))
        self.assertTrue(maze.get_wall(1, 2, Direction.N))
        self.assertTrue(maze.get_wall(0, 1, Direction.E))

    def test_building_twice_changes_nothing(self) -> None:
        maze = self.open_maze(3, 3)
        maze.build_wall(1, 1, Direction.N)
        before = self.snapshot(maze)
        maze.build_wall(1, 1, Direction.N)
        self.assertEqual(before, self.snapshot(maze))

    def test_no_side_at_all_is_a_no_operation(self) -> None:
        maze = self.open_maze(3, 3)
        before = self.snapshot(maze)
        maze.build_wall(1, 1, Direction(0))
        self.assertEqual(before, self.snapshot(maze))

    def test_the_maze_stays_coherent(self) -> None:
        maze = self.open_maze(4, 4)
        maze.build_wall(1, 1, Direction.N | Direction.E)
        maze.build_wall(2, 2, ALL_WALLS)
        self.assert_coherent(maze)


class TestDestroyWall(MazeTest):
    """Destroying is the mirror of building, minus the border."""

    def test_clears_the_side_asked_for(self) -> None:
        maze = Maze(3, 3)
        maze.destroy_wall(1, 1, Direction.N)
        self.assertFalse(maze.get_wall(1, 1, Direction.N))

    def test_clears_the_opposite_side_of_the_neighbour(self) -> None:
        maze = Maze(3, 3)
        maze.destroy_wall(1, 1, Direction.N)
        self.assertFalse(maze.get_wall(1, 0, Direction.S))

    def test_leaves_the_other_sides_alone(self) -> None:
        """Only one bit goes down, the cell does not become 0."""
        maze = Maze(3, 3)
        maze.destroy_wall(1, 1, Direction.N)
        self.assertTrue(maze.get_wall(1, 1, Direction.E))
        self.assertTrue(maze.get_wall(1, 1, Direction.S))
        self.assertTrue(maze.get_wall(1, 1, Direction.W))

    def test_several_sides_at_once(self) -> None:
        maze = Maze(3, 3)
        maze.destroy_wall(1, 1, ALL_WALLS)
        self.assertEqual(int(maze.grid[1][1]), 0)

    def test_destroying_twice_changes_nothing(self) -> None:
        maze = Maze(3, 3)
        maze.destroy_wall(1, 1, Direction.N)
        before = self.snapshot(maze)
        maze.destroy_wall(1, 1, Direction.N)
        self.assertEqual(before, self.snapshot(maze))

    def test_no_side_at_all_is_a_no_operation(self) -> None:
        maze = Maze(3, 3)
        before = self.snapshot(maze)
        maze.destroy_wall(1, 1, Direction(0))
        self.assertEqual(before, self.snapshot(maze))

    def test_a_border_wall_is_refused(self) -> None:
        """The subject requires walls all around the maze."""
        maze = Maze(3, 3)
        for (col, row), side in ((((0, 0)), Direction.N),
                                 (((0, 0)), Direction.W),
                                 (((2, 2)), Direction.S),
                                 (((2, 2)), Direction.E)):
            with self.assertRaises(ValueError):
                maze.destroy_wall(col, row, side)

    def test_the_message_names_the_side_and_the_cell(self) -> None:
        with self.assertRaises(ValueError) as caught:
            Maze(3, 3).destroy_wall(0, 0, Direction.N)
        self.assertIn("N", str(caught.exception))
        self.assertIn("(0, 0)", str(caught.exception))

    def test_a_refused_request_changes_nothing(self) -> None:
        """S and E are legal here, but N is not: nothing may move."""
        maze = Maze(3, 3)
        before = self.snapshot(maze)
        with self.assertRaises(ValueError):
            maze.destroy_wall(0, 0, ALL_WALLS)
        self.assertEqual(before, self.snapshot(maze))

    def test_build_after_destroy_returns_to_closed(self) -> None:
        maze = Maze(3, 3)
        maze.destroy_wall(1, 1, Direction.W)
        maze.build_wall(1, 1, Direction.W)
        self.assertTrue(maze.no_access(1, 1))
        self.assertTrue(maze.no_access(0, 1))

    def test_the_maze_stays_coherent(self) -> None:
        maze = Maze(4, 4)
        maze.destroy_wall(1, 1, Direction.N | Direction.E)
        maze.destroy_wall(2, 2, ALL_WALLS)
        self.assert_coherent(maze)


class TestAdjacentPoints(MazeTest):
    """Which cells exist around another one, walls ignored."""

    def test_an_inner_cell_has_four(self) -> None:
        maze = Maze(3, 3)
        self.assertEqual(sorted(maze.adjacent_points(1, 1)),
                         [(0, 1), (1, 0), (1, 2), (2, 1)])

    def test_a_border_cell_has_three(self) -> None:
        self.assertEqual(len(Maze(3, 3).adjacent_points(0, 1)), 3)

    def test_a_corner_has_two(self) -> None:
        maze = Maze(3, 3)
        self.assertEqual(sorted(maze.adjacent_points(0, 0)),
                         [(0, 1), (1, 0)])

    def test_the_only_cell_of_a_1x1_maze_has_none(self) -> None:
        self.assertEqual(Maze(1, 1).adjacent_points(0, 0), [])

    def test_the_walls_are_ignored(self) -> None:
        """A closed maze and an open one answer the same thing."""
        closed = Maze(3, 3)
        self.assertEqual(closed.adjacent_points(1, 1),
                         self.open_maze(3, 3).adjacent_points(1, 1))

    def test_every_cell_returned_exists(self) -> None:
        maze = Maze(4, 3)
        for col, row in self.cells(maze):
            for point in maze.adjacent_points(col, row):
                self.assertTrue(maze._is_inside(*point))


class TestNeighboursPoints(MazeTest):
    """Which cells can be reached, walls taken into account."""

    def test_a_closed_maze_reaches_nothing(self) -> None:
        maze = Maze(3, 3)
        for col, row in self.cells(maze):
            self.assertEqual(maze.neighbours_points(col, row), [])

    def test_an_open_passage_is_returned(self) -> None:
        maze = Maze(3, 3)
        maze.destroy_wall(1, 1, Direction.E)
        self.assertEqual(maze.neighbours_points(1, 1), [(2, 1)])

    def test_several_open_passages(self) -> None:
        maze = Maze(3, 3)
        maze.destroy_wall(1, 1, Direction.E)
        maze.destroy_wall(1, 1, Direction.S)
        self.assertEqual(sorted(maze.neighbours_points(1, 1)),
                         [(1, 2), (2, 1)])

    def test_the_passage_works_both_ways(self) -> None:
        maze = Maze(3, 3)
        maze.destroy_wall(1, 1, Direction.E)
        self.assertEqual(maze.neighbours_points(2, 1), [(1, 1)])

    def test_reachable_cells_are_adjacent_cells(self) -> None:
        maze = Maze(4, 3)
        maze.destroy_wall(1, 1, ALL_WALLS)
        for col, row in self.cells(maze):
            self.assertLessEqual(set(maze.neighbours_points(col, row)),
                                 set(maze.adjacent_points(col, row)))

    def test_an_open_border_still_returns_no_outside_cell(self) -> None:
        """destroy_wall refuses it, but the grid is checked anyway."""
        maze = Maze(3, 3)
        maze.grid[0][0] &= ~Direction.N
        self.assertEqual(maze.neighbours_points(0, 0), [])

    def test_the_only_cell_of_a_1x1_maze_reaches_nothing(self) -> None:
        self.assertEqual(Maze(1, 1).neighbours_points(0, 0), [])


class TestRandomCarving(MazeTest):
    """The invariants hold after a long run of random operations."""

    def carved(self) -> Maze:
        """Carve a 12x9 maze at random, with a fixed seed."""
        random.seed(42)
        maze = Maze(12, 9)
        for _ in range(400):
            col, row = random.randrange(12), random.randrange(9)
            try:
                maze.destroy_wall(col, row, random.choice(SIDES))
            except ValueError:
                pass          # a border wall, refused on purpose
        for _ in range(60):
            maze.build_wall(random.randrange(12), random.randrange(9),
                            random.choice(SIDES))
        return maze

    def test_walls_agree_between_neighbours(self) -> None:
        self.assert_coherent(self.carved())

    def test_the_border_stays_closed(self) -> None:
        self.assert_border_closed(self.carved())

    def test_reachability_is_symmetric(self) -> None:
        """If b can be reached from a, then a can be reached from b."""
        maze = self.carved()
        for col, row in self.cells(maze):
            for point in maze.neighbours_points(col, row):
                self.assertIn((col, row), maze.neighbours_points(*point))

    def test_no_cell_outside_the_grid_is_ever_returned(self) -> None:
        maze = self.carved()
        for col, row in self.cells(maze):
            for point in maze.neighbours_points(col, row):
                self.assertTrue(maze._is_inside(*point))

    def test_something_was_actually_carved(self) -> None:
        """Guard against a test that would pass on an untouched maze."""
        maze = self.carved()
        self.assertTrue(any(not maze.no_access(col, row)
                            for col, row in self.cells(maze)))


if __name__ == "__main__":
    unittest.main()
