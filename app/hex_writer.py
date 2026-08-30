"""Writing the maze in the output format required by the subject.

One hexadecimal digit per cell (bit 0 = N, 1 = E, 2 = S, 3 = W, 1 =
closed), then a blank line and three lines: entry, exit and shortest
path. Entry and exit go back to the ``x,y`` format.
"""

# TODO: API not agreed yet.
