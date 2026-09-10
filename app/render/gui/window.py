"""MiniLibX window, keys, and animation.

Display is the library: connection, window, pixel buffer, event loop.
MazeWindow is the app: what the keys do, and which frame to show.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, replace
from time import monotonic
from typing import Any, Callable

from mazegen import Maze, Path

from .draw import (HEAD, LINE, MARGIN, STANDARD_SKIN, TAIL, TAIL_LINES, Canvas,
                   Layout, Scene, Skin, colour, draw, write_line)
from .font import CHARACTER

# Room the desktop keeps (panels, title bar), taken off the screen
# before the maze is fitted.
DESKTOP = (120, 160)

# Seconds between animation frames. carve() yields after every wall.
FRAME = 0.012

# X event for the window close button.
DESTROY_NOTIFY = 33

ESCAPE = 65307
LEFT = 65361
UP = 65362
RIGHT = 65363
DOWN = 65364
KEYPAD_LEFT = 65430
KEYPAD_UP = 65431
KEYPAD_RIGHT = 65432
KEYPAD_DOWN = 65433

ARROWS = {
    LEFT: "left",
    UP: "up",
    RIGHT: "right",
    DOWN: "down",
    KEYPAD_LEFT: "left",
    KEYPAD_UP: "up",
    KEYPAD_RIGHT: "right",
    KEYPAD_DOWN: "down",
}

WALL_COLOURS = ("chambray", "vermilion", "gamboge", "peppermint",
                "ultramarine")
FORTY_TWO_COLOURS = ("robin", "cadmium", "flamingo", "verdigris", "snow")

KEYS = (
    "R generate   P path   Q quit",
    "C wall colour   F 42 colour",
    "G gen. alg.   A gen. anim.   S solver alg.   V solver anim.",
)

MIN_WINDOW_WIDTH = max(len(line) for line in KEYS) * CHARACTER + 2 * MARGIN


def key_letter(keysym: int) -> str:
    """X keysym → the letter we answer, or empty."""
    if keysym == ESCAPE:
        return "\x1b"
    if keysym in ARROWS:
        return ARROWS[keysym]
    if 32 <= keysym <= 126:
        return chr(keysym).lower()
    return ""


def path_prefixes(path: Path) -> Iterator[Path]:
    """The route revealed one cell at a time, empty first."""
    for end in range(len(path) + 1):
        yield path[:end]


@dataclass
class Playback:
    """Frames of a maze being carved, then a finished Scene."""

    frames: Iterator[Maze]
    finish: Callable[[Maze], Scene]


class Display:
    """MiniLibX: connection, window, pixel buffer, event loop.

    mlx_init → screen size → mlx_new_window → mlx_new_image
    → hooks → mlx_loop → destroy / mlx_release.
    """

    def __init__(self) -> None:
        # Imported here so tests can draw without MiniLibX installed.
        from mlx import Mlx

        self.mlx = Mlx()
        self.ptr = self.mlx.mlx_init()
        self.window: Any = None
        self.canvas: Canvas | None = None

    def screen_size(self) -> tuple[int, int]:
        _, width, height = self.mlx.mlx_get_screen_size(self.ptr)
        return width, height

    def open(self, width: int, height: int, title: str) -> Canvas:
        self.window = self.mlx.mlx_new_window(self.ptr, width, height, title)
        self.canvas = Canvas(self.mlx, self.ptr, width, height)
        return self.canvas

    def bind(self, on_draw: Callable[..., None],
             on_key: Callable[..., None],
             on_close: Callable[..., None]) -> None:
        self.mlx.mlx_expose_hook(self.window, on_draw, 0)
        self.mlx.mlx_key_hook(self.window, on_key, 0)
        self.mlx.mlx_hook(self.window, DESTROY_NOTIFY, 0, on_close, 0)

    def present(self) -> None:
        """Copy the pixel buffer onto the window and flush."""
        assert self.canvas is not None
        self.mlx.mlx_put_image_to_window(
            self.ptr, self.window, self.canvas.image, 0, 0)
        self.mlx.mlx_do_sync(self.ptr)

    def set_tick(self, callback: Callable[..., None] | None) -> None:
        self.mlx.mlx_loop_hook(self.ptr, callback, 0)

    def exit(self) -> None:
        self.mlx.mlx_loop_exit(self.ptr)

    def run(self) -> None:
        self.mlx.mlx_do_key_autorepeatoff(self.ptr)
        try:
            self.mlx.mlx_loop(self.ptr)
        finally:
            self.mlx.mlx_do_key_autorepeaton(self.ptr)
        assert self.canvas is not None
        self.mlx.mlx_destroy_image(self.ptr, self.canvas.image)
        self.mlx.mlx_destroy_window(self.ptr, self.window)
        self.mlx.mlx_release(self.ptr)


class MazeWindow:
    """A maze on screen, and the keys that change it.

    MiniLibX owns the loop. This class only registers callbacks:
    expose → draw, key → command, loop hook → next animation frame.
    Generation and solving stay outside: ``on_maze`` is asked.
    """

    def __init__(self, scene: Scene, skin: Skin = STANDARD_SKIN,
                 on_maze: Callable[[str, bool], Scene | Playback | None]
                 | None = None) -> None:
        self.display = Display()
        self.scene = scene
        self.skin = skin
        self.on_maze = on_maze
        self.show_path = False
        self.gen_anim = False
        self.solver_anim = False
        self.wall_colour = 0
        self.forty_two_colour = 0
        self._frames: Iterator[None] | None = None
        self._carving = False
        self._due = 0.0

        across, down = self.display.screen_size()
        self.layout = Layout.fit(
            scene.maze, (across - DESKTOP[0], down - DESKTOP[1]),
            min_width=MIN_WINDOW_WIDTH)
        window_width, window_height = self.layout.window
        self.canvas = self.display.open(
            window_width, window_height, scene.title or "maze")

    def run(self) -> None:
        self.display.bind(self.draw, self._on_key, self._on_close)
        self.draw()
        self.display.run()

    def draw(self, _param: Any = None) -> None:
        """Maze + captions into the buffer, then blit."""
        draw(self.canvas, self.scene.maze, self.layout, self.skin,
             self.scene.path if self.show_path else ())
        write_line(self.canvas, self.scene.title, HEAD - LINE,
                   self.skin.title)
        bottom = self.layout.window[1] - TAIL
        lines = [*self.scene.message, "", *self._legend()][-TAIL_LINES:]
        for number, text in enumerate(lines):
            write_line(self.canvas, text, bottom + (number + 1) * LINE,
                       self.skin.message)
        self.display.present()

    def _legend(self) -> list[str]:
        keys = list(KEYS)
        keys[0] = keys[0].replace(
            "P path", "P hide path" if self.show_path else "P path")
        keys[-1] = keys[-1].replace(
            "A gen. anim.", "A gen. on" if self.gen_anim else "A gen. anim.")
        keys[-1] = keys[-1].replace(
            "V solver anim.",
            "V solver on" if self.solver_anim else "V solver anim.")
        return keys

    def _on_key(self, keysym: int, _param: Any = None) -> None:
        self._apply(key_letter(keysym))

    def _on_close(self, _param: Any = None) -> None:
        self.display.exit()

    def _apply(self, key: str) -> None:
        if key in ("\x1b", "q"):
            self.display.exit()
            return
        if key == "a":
            self.gen_anim = not self.gen_anim
        elif key == "v":
            self.solver_anim = not self.solver_anim
        elif key == "p":
            if self.show_path:
                self.show_path = False
            elif self.solver_anim and self.scene.path:
                self._animate(self._reveal_path(self.scene.path))
                return
            else:
                self.show_path = True
        elif key == "c":
            self.wall_colour = (self.wall_colour + 1) % len(WALL_COLOURS)
            self.skin = replace(
                self.skin, wall=colour(WALL_COLOURS[self.wall_colour]))
        elif key == "f":
            self.forty_two_colour = ((self.forty_two_colour + 1)
                                     % len(FORTY_TWO_COLOURS))
            self.skin = replace(
                self.skin,
                forty_two=colour(FORTY_TWO_COLOURS[self.forty_two_colour]))
        elif self.on_maze is not None:
            if self._carving and key not in ("r", "g"):
                return
            result = self.on_maze(key, self.gen_anim)
            if result is None:
                return
            if isinstance(result, Playback):
                self._animate(self._carve(result))
                return
            self._stop()
            self.scene = result
        else:
            return
        self.draw()

    # --- animation: one iterator, one tick ---

    def _animate(self, frames: Iterator[None]) -> None:
        """Each next() updates the scene; we draw after it."""
        self._stop()
        self._frames = frames
        self._due = monotonic()
        self.display.set_tick(self._tick)
        self._tick()

    def _tick(self, _param: Any = None) -> None:
        if self._frames is None or monotonic() < self._due:
            return
        self._due = monotonic() + FRAME
        try:
            next(self._frames)
        except StopIteration:
            self._stop()
            return
        self.draw()

    def _stop(self) -> None:
        self._frames = None
        self._carving = False
        self.display.set_tick(None)

    def _carve(self, play: Playback) -> Iterator[None]:
        self._carving = True
        maze = None
        for maze in play.frames:
            self.scene.maze = maze
            self.scene.path = ()
            yield
        self.scene = play.finish(
            maze if maze is not None else self.scene.maze)
        self._carving = False
        if self.solver_anim and self.scene.path:
            yield from self._reveal_path(self.scene.path)
        else:
            yield

    def _reveal_path(self, path: Path) -> Iterator[None]:
        self.show_path = True
        for prefix in path_prefixes(path):
            self.scene.path = prefix
            yield


def show(scene: Scene, skin: Skin = STANDARD_SKIN,
         on_maze: Callable[[str, bool], Scene | Playback | None] | None = None
         ) -> None:
    """Open a window on that maze and run until the user leaves."""
    MazeWindow(scene, skin, on_maze).run()
