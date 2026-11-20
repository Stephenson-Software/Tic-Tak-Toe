"""Tic Tac Toe's 3D view in the browser (the arcade's pygbag build).

The browser game is the 2D game, and the page's 2D/3D button (graphik's
pygbag template) only changes how it is shown. The page starts in 3D, as
the desktop game does, unless the player chose 2D there before (the page
remembers it) or the address says ?view=2d. WebTicTacToe draws every frame
on the 2D canvas as always, and its Graphik also records what each screen
drew (its headline, its buttons); while 3D is on, that frame is sent to the
page's Strata grid relay as the same scene the desktop 3D window draws
(scene.buildScene, through graphik's Grid3DWebView). So every screen,
button, pause and rule is the 2D game's own, and the view can be switched
either way at any moment, in the middle of a game too:

- presses on the 3D view land on the relay's canvas, which covers pygame's,
  so they are read from the relay: the left button's press (a tap on a
  phone) is matched against the frame's buttons as they appear in 3D (a
  cell's tile through pickCell, a panel through graphik's Button hit test)
  and runs the same handler a 2D press would, once per press, as in 2D;
- the mouse's position over the 3D view lifts the button or tile under it,
  as graphik lifts a 2D button under the cursor (a touch has no hover);
- presses made during a pause are dropped in 3D as in 2D, and the 3D view
  keeps following the button while the game pauses;
- the headlines and buttons keep out from under the page's 2D/3D button
  (graphik's buttonArea(), read when the 3D view opens and on a resize).

If the 3D view can't start, the 2D view stays and the page and the game say
why, in plain words; a page in 2D downloads nothing of the 3D view until
the button asks for it.
"""

import asyncio
import time

from preponderous.graphik.grid3d import Unavailable
from preponderous.graphik.grid3d import web as grid3dweb
from strata_view.scene import (
    ScreenRecorder,
    boardCells,
    buildScene,
    buttonHit,
    frameButtons,
)
from tictactoe import TicTacToe

VIEW_TITLE = "Tic Tac Toe (3D)"
# the 3D view's size gate: Strata's relay is about 1.3 MB; anything far
# bigger than that is not the file this build was made with
MAX_3D_BYTES = 4000000
LEFT_BUTTON = 1
# how long the 2D screen says the 3D view couldn't load
NOTICE_SECONDS = 8.0
# how often a pause looks at the toggle (a pause is up to a second long)
PAUSE_STEP_SECONDS = 0.05


class BrowserPage:
    """The page around the game under pygbag: its 2D/3D button, its size
    and its grid relay (graphik's grid3d.web)."""

    def wants3D(self):
        return grid3dweb.wants3D()

    def set3D(self, on, reason=""):
        grid3dweb.set3D(on, reason)

    def size(self):
        window = _platformWindow()
        return int(window.innerWidth), int(window.innerHeight)

    def unavailable(self):
        """Why the page marked its 3D view unavailable, or "" (its toggle
        keeps the reason after the relay itself is closed)."""
        toggle = grid3dweb.pageObject("Graphik3D")
        return str(toggle.unavailable()) if toggle is not None else ""

    def buttonArea(self):
        """Where the page's 2D/3D button is, (x, y, width, height), for the
        3D view to keep its text and buttons out from under it."""
        return grid3dweb.buttonArea()

    def openView(self, width, height):
        return grid3dweb.Grid3DWebView.open(
            width, height, title=VIEW_TITLE, maxBytes=MAX_3D_BYTES
        )


def _platformWindow():
    import platform  # pygbag's, not the standard library's

    return platform.window


def unavailableLines(reason):
    """What the 2D screen says when the 3D view can't load, in words a
    player can act on."""
    reason = str(reason).strip().rstrip(".") or "it could not load"
    return ["No 3D view here: %s." % reason, "The 2D view stays."]


class Press3D(tuple):
    """Where a press landed on the 3D view, in its own pixels (a 2D press is
    a plain tuple in the 2D window's)."""


class RecordingGraphik:
    """Graphik for the browser game: draws on the 2D canvas as always and
    also keeps what was drawn (a ScreenRecorder) for the 3D view."""

    def __init__(self, graphik, recorder):
        self.graphik = graphik
        self.recorder = recorder

    def drawText(self, *args):
        self.graphik.drawText(*args)
        self.recorder.drawText(*args)

    def drawRectangle(self, *args):
        self.graphik.drawRectangle(*args)
        self.recorder.drawRectangle(*args)

    def drawButton(self, *args):
        self.graphik.drawButton(*args)
        self.recorder.drawButton(*args)

    def __getattr__(self, name):
        return getattr(self.graphik, name)


class WebTicTacToe(TicTacToe):
    """The browser game, with the page's 3D view when the player asks."""

    def __init__(self, page=None, clock=time.monotonic):
        self.page = page if page is not None else BrowserPage()
        self.noticeClock = clock
        self.view3d = None
        self.recorder = ScreenRecorder()
        # the mouse over the 3D view, for hover (None for a touch)
        self.pointer3D = None
        self.sentScene = None
        self.notice = None
        self.noticeUntil = 0.0
        # the page's 2D/3D button, which the 3D headlines and buttons keep clear of
        self.keepClear = None
        # whether a 3D view that failed before the game began has been explained
        self.toldEarlyFailure = False
        super().__init__()

    def initializeDisplay(self):
        super().initializeDisplay()
        self.graphik = RecordingGraphik(self.graphik, self.recorder)

    # -- the toggle

    def follow3DToggle(self):
        """Opens or closes the 3D view to match the page's toggle."""
        if not self.toldEarlyFailure:
            # the page starts loading 3D before the game runs, so it may have failed already
            self.toldEarlyFailure = True
            unavailable = getattr(self.page, "unavailable", None)
            reason = unavailable() if unavailable is not None else ""
            if reason:
                self.showNotice(unavailableLines(reason))
        wanted = self.page.wants3D()
        if wanted and self.view3d is None:
            self.open3D()
        elif not wanted and self.view3d is not None:
            self.close3D()

    def open3D(self):
        try:
            width, height = self.page.size()
            self.view3d = self.page.openView(width, height)
        except Unavailable as reason:
            self.view3d = None
            self.page.set3D(False, str(reason))
            self.showNotice(unavailableLines(reason))
            return
        self.readButtonArea()
        self.pointer3D = None
        self.sentScene = None

    def readButtonArea(self):
        """Where the page's 2D/3D button is now (read on opening and on a
        resize, as the page lays it out)."""
        area = getattr(self.page, "buttonArea", None)
        self.keepClear = area() if area is not None else None

    def close3D(self):
        """Back to the 2D view; if the 3D view failed to load, the 2D screen
        says why."""
        view, self.view3d = self.view3d, None
        reason = view.failure()
        if not reason:
            # the page may have closed the relay itself on a failure, keeping the reason
            unavailable = getattr(self.page, "unavailable", None)
            reason = unavailable() if unavailable is not None else ""
        view.close()
        self.pointer3D = None
        if reason:
            self.showNotice(unavailableLines(reason))

    def showNotice(self, lines):
        self.notice = lines
        self.noticeUntil = self.noticeClock() + NOTICE_SECONDS

    def pointerOn3D(self):
        """True while presses come from the 3D view: it takes the pointer
        once it is drawing, and until then presses reach the 2D canvas."""
        return self.view3d is not None and self.view3d.ready

    # -- drawing

    def update3D(self):
        """The 3D view follows the toggle and shows the frame drawn so far."""
        self.follow3DToggle()
        if self.view3d is not None:
            self.draw3D()

    def draw3D(self):
        """Sends the frame the screen drew (the board, its headline and
        buttons, the hover) unless the 3D view already shows it."""
        view = self.view3d
        cells = boardCells(self)
        key = (
            sorted(cells.items()),
            list(self.recorder.texts),
            list(self.recorder.buttons),
            self.pointer3D,
            view.width,
            view.height,
            self.keepClear,
        )
        if key == self.sentScene:
            return
        buttons = [button for button, _ in self.frameButtons()]
        view.drawScene(
            buildScene(cells, self.recorder.texts, buttons, view.width, view.height, self.pointer3D,
                       self.keepClear)
        )
        self.sentScene = key

    def frameButtons(self):
        return frameButtons(self.buttons, self.recorder.buttons)

    def beginFrame(self):
        super().beginFrame()
        self.recorder.clear()

    def presentNow(self):
        # the player's mark is shown before the computer's pause, in 3D too
        super().presentNow()
        self.update3D()

    def drawNotice(self):
        if self.notice is None:
            return
        if self.noticeClock() >= self.noticeUntil:
            self.notice = None
            return
        for i, line in enumerate(self.notice):
            # on the 2D canvas only: the notice is about the 3D view
            self.graphik.graphik.drawText(
                line, self.displayWidth // 2, self.displayHeight - 60 + 26 * i, 18, self.black
            )

    async def endFrame(self, pressPos):
        self.update3D()
        self.drawNotice()
        await super().endFrame(pressPos)

    async def pause(self, seconds):
        """The 2D game's pause, during which the 3D view still follows the
        toggle (so it can be switched while the computer thinks). It ends on
        time however long the browser takes to come back from each short
        sleep."""
        end = time.monotonic() + seconds
        steps = max(1, int(round(seconds / PAUSE_STEP_SECONDS)))
        for _ in range(steps):
            self.update3D()
            remaining = end - time.monotonic()
            if remaining <= 0:
                break
            await asyncio.sleep(min(seconds / steps, remaining))
        self.update3D()

    # -- input

    def read3DInput(self):
        """The relay's events since the last read: resizes and the mouse's
        position are followed, and the last left-button press (a Press3D) is
        returned, or None."""
        if self.view3d is None:
            return None
        view = self.view3d
        press = None
        for event in view.pollEvents():
            mouse = getattr(event, "pointer", "") != "touch"
            if event.type == grid3dweb.EVENT_RESIZED and event.width and event.height:
                view.resize(event.width, event.height)
                self.readButtonArea()
            elif event.type == grid3dweb.EVENT_MOUSE_MOTION:
                self.pointer3D = (event.x, event.y) if mouse else None
            elif event.type == grid3dweb.EVENT_MOUSE_BUTTON_DOWN and event.button == LEFT_BUTTON:
                press = Press3D((event.x, event.y))
                self.pointer3D = (event.x, event.y) if mouse else None
        return press

    def readEvents(self):
        # As in 2D: where a left-button press landed since the last frame, or None; on the 3D
        # view once it is drawing, on the 2D canvas until then
        pressPos = super().readEvents()
        press3D = self.read3DInput()
        if press3D is not None and self.pointerOn3D():
            return press3D
        return pressPos

    def discardPressesMadeDuringThePause(self):
        # the 2D rule, on the 3D view as well
        super().discardPressesMadeDuringThePause()
        self.read3DInput()

    async def pressButton(self, pressPos):
        if not isinstance(pressPos, Press3D):
            await super().pressButton(pressPos)
            return
        if self.view3d is None:
            return  # switched back to 2D since the press: it was aimed at the 3D view
        width, height = self.view3d.width, self.view3d.height
        for button, function in self.frameButtons():
            if buttonHit(button, pressPos, width, height, self.keepClear):
                await function()
                return
