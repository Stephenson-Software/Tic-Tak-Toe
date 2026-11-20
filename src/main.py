# Entry point for the browser build: pygbag (https://pygame-web.github.io) packages this
# folder and runs main.py. The desktop entry point stays src/tictactoe.py.
#
# In a browser the game is WebTicTacToe: the same 2D game, which also draws itself in the
# page's 3D view when the player turns that on (strata_view/web.py). The 3D view's files are
# downloaded only then.
import asyncio
import sys

# pygbag decides which packages to load into the browser from main.py's own imports, so
# pygame must be imported here even though only tictactoe.py uses it directly.
import pygame  # noqa: F401

from tictactoe import TicTacToe


def chooseGame(platform=None):
    # The game class to run: WebTicTacToe in a browser, so the page's 3D toggle works;
    # TicTacToe anywhere else, or when graphik's 3D view isn't in the build (then the toggle
    # is marked unavailable, with the reason)
    platform = sys.platform if platform is None else platform
    if platform != "emscripten":
        return TicTacToe
    try:
        from strata_view.web import WebTicTacToe
    except ImportError as error:
        print("No 3D view in this build:", error)
        try:
            from preponderous.graphik.grid3d.web import set3D

            set3D(False, "this build has no 3D view")
        except ImportError:
            pass
        return TicTacToe
    return WebTicTacToe


asyncio.run(chooseGame()().titleScreen())
