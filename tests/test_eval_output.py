"""The output file, and the verdict the evaluator's analyzer gives it.

Two questions of the evaluation sheet are settled by one file on disk.
"Output file / Format" asks that the maze on screen also be written
out as:

    HEIGHT lines of WIDTH characters
    an empty line
    the ENTRY tuple
    the EXIT tuple
    the shortest path, in the directions N, E, S and W

and "Maze Generator module" asks that ``python3 maze_analyzer.py`` on
that file report a PERFECT maze for ``PERFECT=True`` and a
Pac-Man-USABLE board for the default.  That script ships with the
subject and is the only judge the defence actually consults, so it is
run here rather than imitated.

``a_maze_ing.py`` does not write the file yet.  Until it does, the
encoding lives in ``write_output`` below, which is the one thing in
this file that will have to change: when the program grows a writer,
this helper calls it and every test around it keeps asking exactly
what it asks now.  The tests that need the *program* to have written
something — rather than the maze to be well formed — are the skipped
ones at the bottom, and they are the list of what is left to do.
"""

import subprocess
import sys
import tempfile
import unittest
from collections import deque
from functools import lru_cache
from pathlib import Path

from mazegen import (Cell, Direction, Maze, MazeConfig, MazeGenerator,
                     MazeSolver)
from mazegen import Path as Route  # the cells walked, not a file on disk

ROOT = Path(__file__).resolve().parent.parent
ANALYZER = ROOT / "subject" / "maze_analyzer.py"

# What the analyzer prints, and what the sheet reads it for.
PERFECT_VERDICT = "PERFECT maze"
USABLE_VERDICT = "Pac-Man-USABLE"
BRAIDED_BONUS = "no real dead-end -> bonus-grade"

# One size per mode is enough here: what varies between mazes is asked
# in test_eval_maze.py, and every run of the analyzer costs a process.
WIDTH, HEIGHT = 20, 15
ENTRY: Cell = (0, 0)
EXIT: Cell = (WIDTH - 1, HEIGHT - 1)

STEPS = {(0, -1): "N", (1, 0): "E", (0, 1): "S", (-1, 0): "W"}


@lru_cache(maxsize=None)
def build(perfect: bool, seed: int = 1) -> tuple[Maze, Route]:
    """A finished maze of that mode, and its shortest way through.

    Remembered, because a braided maze costs about half a second to
    build and most of the tests below want the same one.  Nothing here
    writes to a maze, so one copy serves them all.
    """
    config = MazeConfig(WIDTH, HEIGHT, ENTRY, EXIT,
                        perfect=perfect, seed=seed)
    maze = MazeGenerator.from_config(config).generate()
    return maze, MazeSolver.from_config(config).solve(maze)


def directions(route: Route) -> str:
    """The route written the way the subject asks: one letter a step."""
    letters = []
    for before, after in zip(route, route[1:]):
        step = (after[0] - before[0], after[1] - before[1])
        if step not in STEPS:
            raise ValueError(f"{before} and {after} are not neighbours")
        letters.append(STEPS[step])
    return "".join(letters)


def write_output(maze: Maze, route: Route, path: Path) -> None:
    """Write the maze in the subject's format.

    TODO: call the program's own writer once ``a_maze_ing.py`` has one,
    so that what the evaluator reads is what these tests check.

    One hexadecimal digit a cell, uppercase, a row to a line — the
    grid is held in columns, so a line is read across it — then the
    blank line, the two ends as ``col,row``, and the route.
    """
    lines = ["".join(f"{int(maze.grid[col][row]):X}"
                     for col in range(maze.width))
             for row in range(maze.height)]
    entry, exit_cell = maze.get_entry(), maze.get_exit()
    if entry is None or exit_cell is None:
        raise ValueError("a maze written out needs both of its ends")
    lines += ["",
              f"{entry[0]},{entry[1]}",
              f"{exit_cell[0]},{exit_cell[1]}",
              directions(route)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def shortest_length(maze: Maze) -> int:
    """Steps from the entry to the exit, counted independently.

    A breadth-first sweep written here rather than asked of the
    solver, so that the file's route is measured against something
    that has no stake in the answer.
    """
    entry, exit_cell = maze.get_entry(), maze.get_exit()
    if entry is None or exit_cell is None:
        raise ValueError("a maze to be walked needs both of its ends")
    distance = {entry: 0}
    waiting = deque([entry])
    while waiting:
        cell = waiting.popleft()
        if cell == exit_cell:
            return distance[cell]
        for other, _side in maze.passages(*cell):
            if other not in distance:
                distance[other] = distance[cell] + 1
                waiting.append(other)
    raise AssertionError(f"no way from {entry} to {exit_cell}")


def analyze(path: Path, *flags: str) -> str:
    """Run the subject's analyzer over that file and give back its report."""
    finished = subprocess.run(
        [sys.executable, str(ANALYZER), str(path), *flags],
        capture_output=True, text=True, timeout=120)
    if finished.returncode != 0:
        raise AssertionError(
            f"the analyzer failed ({finished.returncode}): "
            f"{finished.stdout}{finished.stderr}")
    return finished.stdout


class OutputFileTest(unittest.TestCase):
    """A written maze, and what a reader finds in it."""

    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "maze.txt"

    def written(self, perfect: bool, seed: int = 1) -> list[str]:
        maze, route = build(perfect, seed)
        write_output(maze, route, self.path)
        self.maze, self.route = maze, route
        return self.path.read_text(encoding="utf-8").splitlines()

    def test_the_grid_is_height_lines_of_width_characters(self) -> None:
        lines = self.written(False)
        grid = lines[:HEIGHT]
        self.assertEqual(len(grid), HEIGHT)
        for number, line in enumerate(grid):
            with self.subTest(line=number):
                self.assertEqual(len(line), WIDTH)

    def test_every_character_of_the_grid_is_a_hex_digit(self) -> None:
        for line in self.written(False)[:HEIGHT]:
            for char in line:
                self.assertIn(char, "0123456789ABCDEF")

    def test_the_grid_is_followed_by_an_empty_line(self) -> None:
        self.assertEqual(self.written(False)[HEIGHT], "")

    def test_the_two_ends_come_after_the_empty_line(self) -> None:
        lines = self.written(False)
        self.assertEqual(lines[HEIGHT + 1], f"{ENTRY[0]},{ENTRY[1]}")
        self.assertEqual(lines[HEIGHT + 2], f"{EXIT[0]},{EXIT[1]}")

    def test_the_path_is_written_in_the_four_directions(self) -> None:
        route = self.written(False)[HEIGHT + 3]
        self.assertNotEqual(route, "")
        self.assertEqual(set(route) - set("NESW"), set())

    def test_the_path_walks_from_the_entry_to_the_exit(self) -> None:
        """Following the letters must land on the exit, and nowhere else."""
        route = self.written(False)[HEIGHT + 3]
        steps = {letter: step for step, letter in STEPS.items()}
        col, row = ENTRY
        for letter in route:
            step_col, step_row = steps[letter]
            col, row = col + step_col, row + step_row
        self.assertEqual((col, row), EXIT)

    def test_every_step_of_the_path_crosses_an_open_wall(self) -> None:
        """The written route has to agree with the written walls.

        The sheet asks the evaluator to check the path against the
        drawing by eye; this is the same question asked of the grid.
        """
        route = self.written(False)[HEIGHT + 3]
        sides = {"N": Direction.N, "E": Direction.E,
                 "S": Direction.S, "W": Direction.W}
        col, row = ENTRY
        for letter in route:
            side = sides[letter]
            self.assertFalse(self.maze.get_wall(col, row, side),
                             f"the {letter} wall of ({col}, {row}) stands")
            col, row = self.maze.across(col, row, side)

    def test_the_path_is_the_shortest_one(self) -> None:
        """Any route reaches the exit; the sheet asks for the shortest.

        Counted again here with a plain breadth-first sweep rather than
        with the solver, so that a solver returning a long way round
        cannot agree with itself.
        """
        route = self.written(False)[HEIGHT + 3]
        self.assertEqual(len(route), shortest_length(self.maze))


class AnalyzerTest(unittest.TestCase):
    """The verdicts the evaluator will read out loud."""

    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "maze.txt"

    def report(self, perfect: bool, *flags: str, seed: int = 1) -> str:
        maze, route = build(perfect, seed)
        write_output(maze, route, self.path)
        return analyze(self.path, *flags)

    def test_the_analyzer_reads_the_file(self) -> None:
        """A malformed grid makes it complain instead of reporting."""
        report = self.report(False)
        self.assertIn(f"Maze size        : {WIDTH} x {HEIGHT}", report)

    def test_the_walls_are_coherent(self) -> None:
        """Incoherent walls are the analyzer's first refusal, and fatal."""
        self.assertIn("Wall coherence   : OK", self.report(False))

    def test_the_exit_is_reachable(self) -> None:
        self.assertIn("(reachable)", self.report(False))

    def test_a_perfect_maze_is_reported_perfect(self) -> None:
        """PERFECT=True must not read as a playable board."""
        report = self.report(True)
        self.assertIn(PERFECT_VERDICT, report)
        self.assertNotIn(USABLE_VERDICT, report)

    def test_the_default_maze_is_reported_pac_man_usable(self) -> None:
        """PERFECT=False must not read as a perfect maze."""
        report = self.report(False)
        self.assertIn(USABLE_VERDICT, report)
        self.assertNotIn(PERFECT_VERDICT, report)

    def test_the_default_maze_earns_the_no_dead_end_bonus(self) -> None:
        """The sheet's braided bonus: --max-dead-ends 0 and still usable."""
        report = self.report(False, "--max-dead-ends", "0")
        self.assertIn(USABLE_VERDICT, report)
        self.assertIn(BRAIDED_BONUS, report)

    def test_the_two_modes_are_told_apart_over_several_seeds(self) -> None:
        """One lucky seed proves nothing; the mode has to decide it."""
        for seed in (2, 3, 4):
            with self.subTest(seed=seed):
                self.assertIn(PERFECT_VERDICT, self.report(True, seed=seed))
                self.assertIn(USABLE_VERDICT, self.report(False, seed=seed))


@unittest.skip("a_maze_ing.py does not write OUTPUT_FILE yet")
class ProgramWritesItTest(unittest.TestCase):
    """What is left once the program itself writes the file.

    Everything above asks whether the *maze* can be written correctly.
    These ask whether the *program* does it, which is what the sheet
    actually grades, and they cannot be answered until it does.  They
    are written out rather than left as a note so that the day the
    writer lands, this decorator comes off and the work is already
    described.
    """

    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.folder_path = Path(self.folder.name)
        self.output = self.folder_path / "maze.txt"
        self.config = self.folder_path / "config.txt"
        self.config.write_text(
            f"WIDTH={WIDTH}\nHEIGHT={HEIGHT}\n"
            f"ENTRY={ENTRY[0]},{ENTRY[1]}\nEXIT={EXIT[0]},{EXIT[1]}\n"
            f"OUTPUT_FILE={self.output}\nPERFECT=False\nSEED=1\n",
            encoding="utf-8")

    def run_program(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "a_maze_ing.py"), str(self.config)],
            cwd=ROOT, input="", capture_output=True, text=True, timeout=120)

    def test_running_the_program_writes_the_output_file(self) -> None:
        self.run_program()
        self.assertTrue(self.output.exists())

    def test_what_it_writes_satisfies_the_analyzer(self) -> None:
        self.run_program()
        self.assertIn(USABLE_VERDICT, analyze(self.output))

    def test_the_file_holds_the_first_maze_shown(self) -> None:
        """The sheet asks for the first maze displayed, not the last.

        With a seed in the config file the maze is settled, so the
        grid on disk has to be the one the library builds from it.
        """
        self.run_program()
        maze, _route = build(False)
        written = self.output.read_text(encoding="utf-8").splitlines()
        expected = ["".join(f"{int(maze.grid[col][row]):X}"
                            for col in range(maze.width))
                    for row in range(maze.height)]
        self.assertEqual(written[:HEIGHT], expected)


if __name__ == "__main__":
    unittest.main()
