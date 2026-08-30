#!/usr/bin/env python3
"""Entry point: ``python3 a_maze_ing.py config.txt``."""

import sys

from app.config import MazeConfig, MazeConfigError


def main() -> int:
    """Read the config, generate the maze, write it out and display it."""
    if len(sys.argv) != 2:
        print("Usage: python3 a_maze_ing.py config.txt",
              file=sys.stderr)
        return 1
    file_path: str = sys.argv[1]
    # Only the call that can fail is wrapped, so a bug further down is
    # not mistaken for a bad configuration file.
    try:
        config = MazeConfig(file_path)
    except MazeConfigError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    config.show_config()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
