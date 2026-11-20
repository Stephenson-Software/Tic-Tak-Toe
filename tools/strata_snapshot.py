"""Renders every Tic Tac Toe screen with the 3D Strata view, headless.

Each shot runs one frame of the game's real screen (title, board, the three
end screens) on a board it could reach, through StrataTicTacToe, and saves a
PNG. Pointer shots show the hover feedback on a button and on a cell.

    python3 tools/strata_snapshot.py --out shots/
"""

import argparse
import asyncio
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)
os.environ.setdefault("DO_NOT_TRACK", "1")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
if sys.platform.startswith("linux"):
    # Linux renders headless through EGL with no window. On Windows, Strata's
    # headless engine is a hidden SDL window, which the dummy driver can't make.
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

# (name, screen method, board rows top to bottom, moves, pointer target)
# A pointer target is a button's text or a (column, row) cell.
SHOTS = [
    ("01-title", "titleScreen", ["   ", "   ", "   "], 0, None),
    ("02-title-hover-start", "titleScreen", ["   ", "   ", "   "], 0, "Start"),
    ("03-board-empty", "gridScreen", ["   ", "   ", "   "], 0, None),
    ("04-board-hover-cell", "gridScreen", ["   ", " X ", "O  "], 2, (2, 0)),
    ("05-board-midgame", "gridScreen", ["X O", " X ", "O  "], 4, None),
    ("06-you-won", "playerWin", ["X O", " X ", "O X"], 5, None),
    ("07-you-lost", "computerWin", ["X O", "XO ", "O X"], 6, None),
    ("08-tie", "tie", ["XOX", "XOO", "OXX"], 9, None),
    ("09-you-won-hover-play-again", "playerWin", ["X O", " X ", "O X"], 5, "Play Again"),
]


class _FrameDrawn(Exception):
    pass


def setBoard(game, rows, moves):
    from strata_view.scene import CELLS

    for _, (column, row), attribute in CELLS:
        mark = rows[row][column]
        setattr(game, attribute, "" if mark == " " else mark)
    game.moves = moves


async def oneFrame(game, screen):
    """Runs the screen until its first frame is drawn, then stops it."""

    async def drawn(pressPos):
        raise _FrameDrawn

    game.endFrame = drawn
    try:
        await getattr(game, screen)()
    except _FrameDrawn:
        pass
    finally:
        del game.endFrame


def pointerFor(game, target):
    from strata_view.scene import buttonRect, cellCenterOnScreen

    width, height = game.windowSize
    if isinstance(target, tuple):
        return cellCenterOnScreen(target, width, height)
    for button, _ in game.frameButtons():
        if button.text == target:
            x, y, w, h = buttonRect(button, width, height)
            return (x + w / 2.0, y + h / 2.0)
    raise SystemExit("no %r button on this screen" % (target,))


async def shoot(game, out):
    async def noPause(seconds):
        pass

    # the end screens' one-second pause before their first frame
    asyncio.sleep = noPause
    for name, screen, rows, moves, target in SHOTS:
        setBoard(game, rows, moves)
        game.pointer = None
        await oneFrame(game, screen)
        if target is not None:
            game.pointer = pointerFor(game, target)
        game.view.drawScene(game.buildScene(), present=False)
        path = os.path.join(out, "tictaktoe-3d-%s.png" % name)
        game.view.savePng(path)
        print(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="strata-shots")
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=600)
    args = parser.parse_args(argv)

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)

    from strata_view.game import StrataTicTacToe, openView

    view = openView(args.width, args.height, window=False)
    try:
        asyncio.run(shoot(StrataTicTacToe(view), out))
    finally:
        view.close()


if __name__ == "__main__":
    main()
