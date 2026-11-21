"""Tic Tac Toe played in a 3D Strata window (desktop only).

StrataTicTacToe is the ordinary game with a different face. Every screen
(title, board, the three end screens), button, pause and rule is
TicTacToe's own: only the window underneath changes. Graphik is replaced by
a ScreenRecorder that keeps what each frame draws, scene.buildScene turns
that into a 3D scene, and a press is matched against the buttons as they
appear in 3D (a cell's tile, or a panel), then handed to the same handler
the 2D window would run.
"""

import asyncio
import sys

from strata_view import StrataUnavailable
from strata_view.scene import (
    LAYOUT_HEIGHT,
    LAYOUT_WIDTH,
    ScreenRecorder,
    boardCells,
    buildScene,
    buttonHit,
    endScreenShift,
    frameButtons,
)
from tictactoe import TicTacToe

LEFT_BUTTON = 1


class StrataTicTacToe(TicTacToe):
    def __init__(self, view):
        # view: a graphik Grid3DView (or a stand-in with the same calls in tests)
        self.view = view
        # where the mouse last was, for hover feedback, and the press waiting to be read
        self.pointer = None
        self.pendingPress = None
        super().__init__()

    # -- the window, in place of pygame's

    def initializeDisplay(self):
        self.graphik = ScreenRecorder()

    @property
    def windowSize(self):
        return self.view.width, self.view.height

    def frameButtons(self):
        """This frame's buttons, each with the handler TicTacToe pressed it with."""
        return frameButtons(self.buttons, self.graphik.buttons)

    def buildScene(self):
        width, height = self.windowSize
        buttons = [button for button, _ in self.frameButtons()]
        return buildScene(boardCells(self), self.graphik.texts, buttons, width, height, self.pointer)

    def render(self):
        self.view.drawScene(self.buildScene())

    def presentNow(self):
        self.render()

    def pollWindow(self):
        strata = self.view.strata
        for event in self.view.pollEvents():
            if event.type == strata.EVENT_QUIT:
                self.closeAndQuit()
            elif event.type == strata.EVENT_MOUSE_BUTTON_DOWN and event.button == LEFT_BUTTON:
                self.pointer = (event.x, event.y)
                self.pendingPress = (event.x, event.y)
            elif event.type == strata.EVENT_MOUSE_MOTION:
                self.pointer = (event.x, event.y)
            elif event.type == strata.EVENT_RESIZED:
                self.view.resize(event.width, event.height)

    def readEvents(self):
        # As in 2D: where a left-button press landed since the last frame, or None
        self.pollWindow()
        pressPos, self.pendingPress = self.pendingPress, None
        return pressPos

    def discardPressesMadeDuringThePause(self):
        # The same rule as the 2D window: a press made during a pause was aimed at the board as
        # it stood, so it is dropped rather than played when the pause ends
        self.pollWindow()
        self.pendingPress = None

    def beginFrame(self):
        self.buttons = []
        self.graphik.clear()

    async def endFrame(self, pressPos):
        self.render()
        # paces the frame as pygame's clock does in 2D, without blocking the event loop
        await asyncio.sleep(1.0 / self.framesPerSecond)
        await self.pressButton(pressPos)

    async def pressButton(self, pressPos):
        width, height = self.windowSize
        pairs = self.frameButtons()
        shift = endScreenShift(boardCells(self), [button for button, _ in pairs], width, height)
        for button, function in pairs:
            if buttonHit(button, pressPos, width, height, shift=shift):
                await function()
                return

    def closeAndQuit(self):
        self.view.close()
        sys.exit()

    async def exit(self):
        self.closeAndQuit()


def openView(width=LAYOUT_WIDTH, height=LAYOUT_HEIGHT, window=True, title="Tic Tac Toe"):
    """A graphik Grid3DView, or StrataUnavailable with a plain reason."""
    try:
        from preponderous.graphik.grid3d import Grid3DView, Unavailable
    except ImportError:
        raise StrataUnavailable(
            "graphik's 3D grid view (preponderous.graphik.grid3d) isn't installed"
        )
    try:
        return Grid3DView.open(width, height, title, headless=not window)
    except Unavailable as reason:
        raise StrataUnavailable(str(reason))


def runStrataGame():
    view = openView()
    try:
        asyncio.run(StrataTicTacToe(view).titleScreen())
    finally:
        view.close()
