"""Tests for MazeConfig and MazeGenerator."""

import unittest

from mazegen import MazeConfig

# TODO: corridor constraint.


class MazeConfigTest(unittest.TestCase):
    """The settings object the generator is built from."""

    def test_it_keeps_the_values(self) -> None:
        config = MazeConfig(
            20, 15, (0, 0), (19, 14), perfect=True, seed=7,
            gen_algorithm="kruskal")
        self.assertEqual(config.width, 20)
        self.assertEqual(config.height, 15)
        self.assertEqual(config.entry_cell, (0, 0))
        self.assertEqual(config.exit_cell, (19, 14))
        self.assertTrue(config.perfect)
        self.assertEqual(config.seed, 7)
        self.assertEqual(config.gen_algorithm, "kruskal")

    def test_optional_fields_default(self) -> None:
        config = MazeConfig(4, 3, (0, 0), (3, 2))
        self.assertFalse(config.perfect)
        self.assertIsNone(config.seed)
        self.assertIsNone(config.gen_algorithm)
        self.assertIsNone(config.solve_algorithm)

    def test_a_zero_size_is_refused(self) -> None:
        with self.assertRaises(ValueError) as caught:
            MazeConfig(0, 3, (0, 0), (0, 2))
        self.assertIn("0x3", str(caught.exception))

    def test_an_exit_outside_the_maze_is_refused(self) -> None:
        with self.assertRaises(ValueError) as caught:
            MazeConfig(4, 3, (0, 0), (9, 9))
        self.assertIn("exit", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
