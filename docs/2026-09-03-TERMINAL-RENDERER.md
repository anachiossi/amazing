# Terminal renderer

**2026-09-03 — Ana (@anade-mo).** Files: `app/render/terminal.py`,
`a_maze_ing.py`, `tests/test_terminal.py`, `tests/test_fit.py`.

Delivers §4.2 of the 2026-08-31 minutes: something to draw with while
the generator is written, before MiniLibX.

## Contract

```python
maze.get_dim()                      # (width, height)
maze.get_wall(col, row, direction)  # True when closed
```

Nothing else is read; `grid` is never touched. Stated as a `Protocol`
(`MazeView`) so mypy enforces it. Per §4.4 this does not change without
an issue first.

`tests/fake_maze.py` deleted — `Maze.randomize()` covers what it was
for.

## Design

**One pass, no surface.** Lines are built top to bottom, left to right,
appended to a string; every character is decided once and never
revisited. A surface-based version (paint, read back, overpaint) was
written first and dropped: 36 functions and 228 lines against 22 and
191, for the same output. Cost of the trade: no drawing *over* — the
order things win is decided inside `_middle`, not by call order.

**Border first, then N and W.** The outside of a maze is walled by
definition, so the four edges are drawn without reading the grid. What
is left is interior, where every wall belongs to two cells and each
cell draws only its north and west — so every wall has exactly one
owner, with no last-row or last-column case. Price: a border broken in
the data does not show; `Maze` refuses to open one, so it takes
reaching past its API.

**Two kinds of line, one way in.**

```python
line(maze, char_row, …)     # divmod picks the kind and the row
  _horizontal_line(…)       # even: horizontal walls, junctions between
  _centre_line(…)           # odd:  upright walls, and cell centres
```

`2 * height + 1` lines; one more horizontal than there are rows, which
is why `render` counts lines rather than rows.

**Junctions are computed, not read back.** `junction()` asks the four
wall segments around a corner and indexes the skin's 16 pieces by the
`Direction` bits (N=1, E=2, S=4, W=8). `horizontal()` / `vertical()`
answer whether a segment is closed; out of range answers False, which
is what leaves a corner with two arms.

## Skins

```python
Element(symbol, ink)               # one thing that can appear
JoinedElement(…, joints)           # 16 pieces, indexed by sides
TerminalSkin(floor, wall, border, entry, exit, paths, meeting,
             title, message, char1, char2)
```

Two ship: `STANDARD_SKIN` (box drawing) and `BLOCKS` (solid `█`, for
cells one character wide). A new look is an instance, not a subclass —
they differ in values, never behaviour.

**No backgrounds.** Every colour is ink; one character holds one thing.
Colours are named through `rainbow` (`src/rainbow`, ships with the
project): `ink=rainbow.ink("gamboge")`. `python3 -m rainbow` lists all
256.

**No special drawing for walled-in cells.** A cell with four walls is
drawn like any other; the "42" shows as the boxes it is made of.

## Paths

`Drawing.paths` is a list of routes, `TerminalSkin.paths` a list of
elements, one per route, plus `meeting`.

```python
paths_links(paths, elements, meeting, goal) -> dict[Cell, (sides, element)]
```

Sides add up where routes share a cell. **Solved** — routes sharing a
cell, or any route reaching `goal` — draws *every* cell of *every* path
in `meeting`. So bidirectional search is two colours until the halves
touch and one colour from that frame on, and a single search turns on
arrival. `Drawing.exit` supplies `goal`.

The sides of a cell index the same 16 pieces the walls use, so a bend
in a route is chosen exactly as a bend in a wall is; the path skin uses
rounded corners so the two never read alike.

## Animation

```python
animate(frames, drawing=None, delay=0.05, reveal=True)
```

A frame is a `MazeView`, or an `AnimationFrame` carrying its own
`Drawing`. With `reveal`, a drawing that has paths is expanded by
`Animation.path_frames()` — every path grows a cell per frame, which is
what makes two halves meet. `reveal=False` draws the frame as it is;
needed to hold a finished route, since otherwise every call regrows it.

The screen is cleared before each frame, never after, so the last
frame stays up and a final `delay=0.0` costs nothing.

Generation animates the same way once the generator yields:

```python
animate(generator.carve(), plan, delay=0.02)
```

## Size

| | where | why |
|---|---|---|
| how big a drawing is — `drawing_size()` | renderer | its own arithmetic |
| which width fits — `widest_that_fits()` | renderer | the same, backwards |
| how big the space is | `a_maze_ing.py` | environment read |
| what to do when nothing fits | `a_maze_ing.py` | error, exit 1 |

Space is passed in, never looked up, so fitting stays pure — tests hand
it a size, MLX will hand it a window. Cells: 3 and 2 use
`STANDARD_SKIN`, 1 uses `BLOCKS`. Lines do not scale (a cell is one
line tall), so height either fits or nothing does; columns are the
dial.

Earlier this arithmetic lived in `a_maze_ing.py` as well as the
renderer and the two drifted twice. The decision still belongs to the
glue; the arithmetic does not.

## Extending

| Want | Change |
|---|---|
| cells taller than one line | `cell_height` in both line builders |
| a visited-cells tint | needs a background on `Element`; absent by choice |
| Pac-Man pellets | `floor=Element("·")` — no code |
| a walking character | `Drawing.char1` moved per frame |
| a third route colour | one more element in `skin.paths` |

## Checking

```bash
make demo         # sizes, then the animations
make run          # config.txt, fitted to the terminal
make test         # 175 cases
make lint-strict  # flake8 + mypy --strict
```

Without the venv, prefix with `PYTHONPATH=src` — `mazegen` and
`rainbow` live under `src/`.

## Stopgaps

`_carve` (recursive backtracker) and `_solve` (BFS) sit at the foot of
`terminal.py` so the demo has a real maze and a real route to draw.
They use only `Maze`'s public API and are not part of the renderer —
they go when the generator and solver land. `_carving` already yields
after each wall opened, which is the shape `animate` expects.
