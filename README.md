<!-- STUB — every section below still has to be written. -->

*This project has been created as part of the 42 curriculum by <login1>, <login2>.*

# A-Maze-ing

> **STUB.** Headings follow the structure the subject requires. Nothing
> below is written yet.

## Description

TODO: what the project is, its goal, a short overview.

## Instructions

TODO: installation, how to run, how to run the tests.

```bash
make install     # dependencies + editable install of mazegen
make run         # python3 a_maze_ing.py config.txt
make test        # unit tests
make lint        # flake8 + mypy
```

## Configuration file

TODO: the complete structure and format of config.txt — mandatory keys
(WIDTH, HEIGHT, ENTRY, EXIT, OUTPUT_FILE, PERFECT), optional keys
(SEED, ALGORITHM), the comment syntax, and the coordinate convention.

## The generation algorithm

TODO: which algorithm was chosen.

## Why this algorithm

TODO: the reasoning behind the choice, and what was rejected.

## Reusable module

TODO: what part of the code is reusable and how. Must cover:

- how to instantiate and use the generator, with a basic example
- how to pass custom parameters (size, seed)
- how to reach the generated structure and at least one solution

```python
# TODO: replace with a working example
from mazegen import MazeGenerationConfig, MazeGenerator

config = MazeGenerationConfig(20, 15, (0, 0), (19, 14))
generator = MazeGenerator.from_config(config)
maze = generator.generate()
```

## Advanced features

TODO: multiple algorithms, display options, bonuses — or remove this
section if none are implemented.

## Team and project management

TODO:

- the role of each team member
- the planning that was anticipated, and how it evolved
- what worked well and what could be improved
- which specific tools were used

## Resources

TODO: classic references on maze generation — documentation, articles,
tutorials.

TODO: how AI was used — for which tasks and which parts of the project.
This is required by the subject, and it is easier to write while the
work is still fresh than to reconstruct later.
