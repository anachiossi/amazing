"""Drawing a maze in Braille, and why it is not the renderer we use.

    python3 experiments/braille_maze.py [width] [height]

A Braille character holds a grid of dots — two across and four down —
so one character can carry what the renderer spends eight on. A 20x15
maze is 41x31 pixels, which is 21 columns by 8 lines instead of the
45 by 36 the terminal renderer asks for. That is the whole appeal.

**What it costs.** A wall one pixel wide lights one dot column out of
two, so it is drawn as a dotted line and not a solid one. This file
draws walls one pixel and cells three, which is the most generous the
idea gets: even here the walls come out dashed, and the "42" is the
only thing that reads as solid, because it is a filled block rather
than a line. A maze is line art, so Braille fights it.

**What was tried.** Using fewer dot rows per character (two or three
instead of four) to even out the vertical rhythm, on the theory that
the gap between character rows is wider than the gaps within one.
It makes it worse: the character cell is a fixed height whatever is
drawn in it, so lighting only the top rows leaves the bottom of every
character empty and the gaps grow.

**What we use instead.** The block skin at one character a cell, which
draws solid walls. Kept here because the packing idea is sound even if
Braille is the wrong alphabet for it: the same fold at one pixel by
two gives half-blocks, which halve the height and keep solid lines.
"""

import sys

import rainbow
from app.render.terminal import horizontal, vertical
from mazegen import Maze, MazeGenerationConfig, MazeGenerator

# Which bit each dot of a Braille character owns, by column and row.
DOTS: dict[tuple[int, int], int] = {
    (0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (0, 3): 0x40,
    (1, 0): 0x08, (1, 1): 0x10, (1, 2): 0x20, (1, 3): 0x80,
}

BRAILLE = 0x2800
STEP = 4          # pixels a cell takes: one of wall, three of floor


def bitmap(maze: Maze) -> list[list[bool]]:
    """The maze as pixels: walls, and the cells the "42" seals."""
    width, height = maze.get_dim()
    cols, rows = STEP * width + 1, STEP * height + 1
    grid = [[False] * cols for _ in range(rows)]
    for row in range(height + 1):
        for col in range(width + 1):
            if col < width and horizontal(maze, col, row):
                for step in range(STEP + 1):
                    grid[STEP * row][STEP * col + step] = True
            if row < height and vertical(maze, col, row):
                for step in range(STEP + 1):
                    grid[STEP * row + step][STEP * col] = True
    # A cell nothing can reach is one of the 42's, which is how the
    # subject's own analyzer picks them out. Asked of the maze rather
    # than of the generator, so a maze read back from a file draws the
    # same as one just carved.
    for row in range(height):
        for col in range(width):
            if maze.no_access(col, row):
                for down in range(1, STEP):
                    for across in range(1, STEP):
                        grid[STEP * row + down][STEP * col + across] = True
    return grid


def packed(grid: list[list[bool]], ink: str = "chambray") -> list[str]:
    """Fold the pixels into Braille, two across and four down."""
    rows, cols = len(grid), len(grid[0])
    lines = []
    for top in range(0, rows, 4):
        line = []
        for left in range(0, cols, 2):
            bits = 0
            for (across, down), bit in DOTS.items():
                row, col = top + down, left + across
                if row < rows and col < cols and grid[row][col]:
                    bits |= bit
            line.append(chr(BRAILLE + bits))
        lines.append(rainbow.write("".join(line), ink=ink))
    return lines


def main(argv: list[str]) -> int:
    """Draw one maze, at whatever size was asked for."""
    width, height = (int(argv[0]), int(argv[1])) if len(argv) > 1 else (20, 15)
    maze = MazeGenerator.from_config(MazeGenerationConfig(
        width, height, (0, 0), (width - 1, height - 1),
        perfect=False, seed=7)).generate()
    grid = bitmap(maze)
    lines = packed(grid)
    # Counted off the pixels, not off the drawn line: the line is
    # carrying its colour with it and that is not width.
    across = (len(grid[0]) + 1) // 2
    print(f"\n{width}x{height} maze, {STEP} pixels a cell "
          f"-> {len(grid[0])}x{len(grid)} pixels "
          f"-> {across} columns x {len(lines)} lines\n")
    print("\n".join(lines))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
