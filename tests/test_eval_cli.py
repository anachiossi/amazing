"""The program as the evaluator runs it, from the command line.

Two sections of ``subject/eval_amazing.pdf`` are about the program
rather than the maze:

* "Standard usage / Display" — running ``a_maze_ing.py`` with a
  default configuration file draws a maze and offers a way to
  interact with it;
* "Configuration file / Error Management" — the evaluator edits the
  configuration file five ways in turn and the program has to handle
  each of them.

Both are graded against one rule that outranks everything else on the
sheet: *no unexpected, premature, uncontrolled or unexpected
termination of the program is allowed, else the final grade is 0*.  So
every test here runs the real program in a real process and asks the
same three questions — what it exited with, what it said, and whether
a traceback reached the terminal.  A traceback is the failure the
sheet is describing, and it is worth catching here rather than at the
defence.

Nothing is typed at the program: with no terminal on standard input it
draws the maze once and stops, which is what makes it testable.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROGRAM = ROOT / "a_maze_ing.py"
CONFIG = ROOT / "config.txt"

# A configuration the evaluator would recognise, and the smallest edit
# away from it each of the sheet's five error cases is.
GOOD = """\
# a maze, written the way the subject asks
WIDTH=18
HEIGHT=9
ENTRY=0,0
EXIT=17,8
OUTPUT_FILE=maze.txt
PERFECT=False
"""

# The window the program is given. Set explicitly so that the size of
# whoever's terminal is running the tests cannot decide the result:
# the renderer refuses a maze it cannot fit, and that refusal is a
# different failure from the ones being asked about here.
ROOM = {"COLUMNS": "200", "LINES": "60"}


def run(*arguments: str, environment: dict[str, str] | None = None
        ) -> subprocess.CompletedProcess[str]:
    """Run the program to completion and give back everything it did."""
    import os

    env = dict(os.environ)
    env.update(ROOM)
    env["PYTHONPATH"] = str(ROOT / "src")
    if environment:
        env.update(environment)
    return subprocess.run(
        [sys.executable, str(PROGRAM), *arguments],
        cwd=ROOT, input="", capture_output=True, text=True,
        timeout=120, env=env)


class ProgramTest(unittest.TestCase):
    """A place to write a configuration file, and the questions to ask."""

    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "config.txt"

    def config(self, text: str) -> str:
        self.path.write_text(text, encoding="utf-8")
        return str(self.path)

    def assert_no_traceback(
            self, finished: subprocess.CompletedProcess[str]) -> None:
        """The sheet's fatal criterion, asked of one run.

        Two ways a program ends without meaning to: an exception that
        reaches the terminal, and a signal that kills it outright — a
        negative status is what ``subprocess`` reports for the second.
        """
        both = finished.stdout + finished.stderr
        self.assertNotIn("Traceback (most recent call last)", both)
        self.assertGreaterEqual(finished.returncode, 0)

    def assert_refused(self, text: str, *words: str) -> str:
        """The program should say no to this configuration, and say why.

        Refused means an error message and a failing exit status — not
        a traceback, and not carrying on with a maze it made up.
        """
        finished = run(self.config(text))
        self.assert_no_traceback(finished)
        self.assertNotEqual(finished.returncode, 0)
        self.assertIn("error", finished.stderr.lower())
        for word in words:
            self.assertIn(word, finished.stderr)
        return finished.stderr


class DisplayTest(ProgramTest):
    """"Standard usage / Display": it runs, it draws, it stops."""

    def test_the_shipped_config_draws_a_maze(self) -> None:
        """The evaluator's first command, run exactly as written."""
        finished = run(str(CONFIG))
        self.assert_no_traceback(finished)
        self.assertEqual(finished.returncode, 0)
        self.assertNotEqual(finished.stdout.strip(), "")

    def test_a_plain_config_draws_a_maze(self) -> None:
        finished = run(self.config(GOOD))
        self.assert_no_traceback(finished)
        self.assertEqual(finished.returncode, 0)

    def test_the_drawing_is_as_wide_as_the_maze_asked_for(self) -> None:
        """A drawn maze, not a message that happens to be on stdout."""
        finished = run(self.config(GOOD))
        drawn = [line for line in finished.stdout.splitlines()
                 if "━" in line or "─" in line]
        self.assertGreaterEqual(len(drawn), 9)

    def test_the_mandatory_interactions_are_offered(self) -> None:
        """"Interactive menu": a new maze, the path, the wall colours.

        The sheet asks for all three by name.  What the keys do is
        tested in test_terminal.py; that the program tells the
        evaluator they exist is asked here.
        """
        finished = run(self.config(GOOD))
        for word in ("redraw", "path", "colour", "quit"):
            with self.subTest(interaction=word):
                self.assertIn(word, finished.stdout)

    def test_asking_for_a_window_without_minilibx_is_refused(self) -> None:
        """--gui on a machine with no MiniLibX must not be a traceback."""
        finished = run(str(CONFIG), "--gui")
        self.assert_no_traceback(finished)

    def test_running_it_with_no_configuration_file(self) -> None:
        finished = run()
        self.assert_no_traceback(finished)
        self.assertNotEqual(finished.returncode, 0)
        self.assertIn("Usage", finished.stderr)

    def test_a_configuration_file_that_is_not_there(self) -> None:
        finished = run(str(Path(self.folder.name) / "absent.txt"))
        self.assert_no_traceback(finished)
        self.assertNotEqual(finished.returncode, 0)


class ErrorManagementTest(ProgramTest):
    """"Configuration file / Error Management", edit by edit.

    The sheet lists five, and each one gets the test it is written as.
    """

    def test_a_mandatory_key_is_removed(self) -> None:
        for key in ("WIDTH", "HEIGHT", "ENTRY", "EXIT",
                    "OUTPUT_FILE", "PERFECT"):
            with self.subTest(missing=key):
                without = "".join(line + "\n"
                                  for line in GOOD.splitlines()
                                  if not line.startswith(key + "="))
                self.assert_refused(without, key)

    def test_a_line_does_not_respect_key_equals_value(self) -> None:
        self.assert_refused(GOOD + "THIS LINE HAS NO EQUALS SIGN\n")

    def test_numbers_are_replaced_by_letters(self) -> None:
        for line, broken in (("WIDTH=18", "WIDTH=eighteen"),
                             ("HEIGHT=9", "HEIGHT=nine")):
            with self.subTest(value=broken):
                self.assert_refused(GOOD.replace(line, broken),
                                    broken.split("=")[0])

    def test_perfect_is_given_something_that_is_not_a_boolean(self) -> None:
        for value in ("maybe", "42", "Tru", ""):
            with self.subTest(perfect=value):
                self.assert_refused(
                    GOOD.replace("PERFECT=False", f"PERFECT={value}"),
                    "PERFECT")

    def test_an_end_is_written_in_the_wrong_format(self) -> None:
        """The sheet's "wrong format of int tuple" for ENTRY or EXIT."""
        for line, broken in (("ENTRY=0,0", "ENTRY=0"),
                             ("ENTRY=0,0", "ENTRY=0,0,0"),
                             ("ENTRY=0,0", "ENTRY=x,y"),
                             ("ENTRY=0,0", "ENTRY=(0, 0)"),
                             ("EXIT=17,8", "EXIT=17;8"),
                             ("EXIT=17,8", "EXIT=")):
            with self.subTest(end=broken):
                self.assert_refused(GOOD.replace(line, broken),
                                    broken.split("=")[0])

    def test_an_end_that_falls_outside_the_maze(self) -> None:
        """Named on the sheet under inconsistent generator parameters."""
        self.assert_refused(GOOD.replace("EXIT=17,8", "EXIT=99,99"), "EXIT")
        self.assert_refused(GOOD.replace("ENTRY=0,0", "ENTRY=-1,0"), "ENTRY")

    def test_a_negative_or_empty_size(self) -> None:
        self.assert_refused(GOOD.replace("WIDTH=18", "WIDTH=-5"), "WIDTH")
        self.assert_refused(GOOD.replace("HEIGHT=9", "HEIGHT=0"), "HEIGHT")

    def test_an_unknown_algorithm_is_named_in_the_message(self) -> None:
        self.assert_refused(GOOD + "GEN_ALGORITHM=nonesuch\n", "kruskal")

    def test_an_empty_configuration_file(self) -> None:
        self.assert_refused("")

    def test_a_file_of_nothing_but_comments(self) -> None:
        self.assert_refused("# everything here is a comment\n# and this too\n")

    def test_a_comment_and_a_blank_line_are_not_errors(self) -> None:
        """The other half of the "Format" question: # starts a comment."""
        finished = run(self.config(
            "# a comment\n\n" + GOOD + "\n   # an indented one\n"))
        self.assert_no_traceback(finished)
        self.assertEqual(finished.returncode, 0)

    def test_the_keys_may_be_written_in_lower_case(self) -> None:
        """The sheet allows it in as many words."""
        finished = run(self.config(GOOD.lower()))
        self.assert_no_traceback(finished)
        self.assertEqual(finished.returncode, 0)


class FortyTwoNoticeTest(ProgramTest):
    """The one thing the sheet asks the program to *say* about the "42".

    "There is the '42' pattern in the maze (except if size does not
    allow it, then you should have a message on the terminal)."  Below
    ``forty_two.MIN_WIDTH`` x ``MIN_HEIGHT`` the pattern is silently
    left out: the maze is drawn as if nothing were missing, and an
    evaluator looking for the "42" is told nothing.
    """

    def test_a_maze_too_small_says_so(self) -> None:
        small = ("WIDTH=8\nHEIGHT=8\nENTRY=0,0\nEXIT=7,7\n"
                 "OUTPUT_FILE=maze.txt\nPERFECT=False\n")
        finished = run(self.config(small))
        self.assert_no_traceback(finished)
        self.assertEqual(finished.returncode, 0)
        self.assertIn("42", finished.stdout + finished.stderr)

    def test_a_maze_with_room_says_nothing_of_the_sort(self) -> None:
        """The notice is for the case that needs it, not for every run."""
        finished = run(self.config(GOOD))
        self.assertNotIn("too small", finished.stdout.lower())


if __name__ == "__main__":
    unittest.main()
