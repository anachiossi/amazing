"""Writing the maze in the output format required by the subject.

One hexadecimal digit per cell (bit 0 = N, 1 = E, 2 = S, 3 = W, 1 =
closed), then a blank line and three lines: entry, exit and shortest
path. Entry and exit are written as ``x,y``, the order they are
already held in, so nothing is converted.

The grid is stored by column, so writing it means looping y on the
outside and x on the inside: one line per row, as the subject wants.
"""

# TODO: API not agreed yet.
