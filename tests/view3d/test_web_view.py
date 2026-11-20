"""The browser's 3D view (src/strata_view/web.py), without a browser.

WebTicTacToe runs against the headless pygame driver and a stand-in page
whose grid relay is graphik's RecordingRelay, which keeps every message the
game sends (graphik's wire decoder reads them back) and hands out scripted
relay events. pygbag's own pieces (the page's toggle and size) are the
stand-in's.
"""

import asyncio
import runpy
import sys

import pygame
import pytest

pytest.importorskip("preponderous.graphik.grid3d.web")

from preponderous.graphik.grid3d import Unavailable  # noqa: E402
from preponderous.graphik.grid3d import web as grid3dweb  # noqa: E402

import tictactoe  # noqa: E402
from strata_view import scene  # noqa: E402
from strata_view import web  # noqa: E402
from strata_view.web import Press3D, WebTicTacToe, unavailableLines  # noqa: E402

PHONE = (390, 844)
DESKTOP = (1280, 800)
SCREENS = ["titleScreen", "gridScreen", "playerWin", "computerWin", "tie"]


class Relay(grid3dweb.RecordingRelay):
    """A RecordingRelay whose events come from `player`, asked for the next
    batch each time the game polls (or from `events`, once)."""

    def __init__(self, state="ready"):
        super().__init__(state=state)
        self.player = None

    def poll(self):
        events = super().poll()
        if self.player is not None:
            events += list(self.player())
        return events


class Page:
    """The page around the game: a 3D toggle, a size and a grid relay."""

    def __init__(self, size=PHONE, failOpen=None, relayState="ready"):
        self.on = False
        self.size_ = size
        self.failOpen = failOpen
        self.relay = Relay(state=relayState)
        self.toggles = []
        self.opened = 0
        self.area = None  # where the 2D/3D button is (buttonArea)

    def buttonArea(self):
        return self.area

    def wants3D(self):
        return self.on

    def set3D(self, on, reason=""):
        self.toggles.append((bool(on), reason))
        self.on = bool(on)

    def size(self):
        return self.size_

    def openView(self, width, height):
        if self.failOpen:
            raise Unavailable(self.failOpen)
        self.opened += 1
        return grid3dweb.Grid3DWebView.open(width, height, relay=self.relay)


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


@pytest.fixture(autouse=True)
def noPauses(monkeypatch):
    async def fakeSleep(seconds):
        pass

    monkeypatch.setattr(tictactoe.asyncio, "sleep", fakeSleep)
    # the browser build: no Quit button
    monkeypatch.setattr(tictactoe.sys, "platform", "emscripten")
    yield
    pygame.quit()


@pytest.fixture
def page():
    return Page()


@pytest.fixture
def game(page):
    return WebTicTacToe(page=page, clock=Clock())


class FrameDrawn(Exception):
    pass


def oneFrame(game, screen):
    """Runs a screen until its first frame has been drawn and sent (the 2D
    endFrame stops it before its press is handled)."""
    original = tictactoe.TicTacToe.endFrame

    async def drawn(self, pressPos):
        raise FrameDrawn

    tictactoe.TicTacToe.endFrame = drawn
    try:
        with pytest.raises(FrameDrawn):
            asyncio.run(getattr(game, screen)())
    finally:
        tictactoe.TicTacToe.endFrame = original


def decoded(page, kind=None):
    messages = [grid3dweb.decode(m) for m in page.relay.messages]
    return [body for k, body in messages if kind is None or k == kind]


def hud(page):
    return decoded(page, grid3dweb.HUD)[-1]


def hudText(page):
    return [label["text"] for label in hud(page)["labels"]]


def event(kind, **fields):
    values = dict(type=kind, button=0, x=0.0, y=0.0, width=0, height=0, pointer="mouse")
    values.update(fields)
    return values


def press(pos, pointer="mouse", button=1):
    return [event(grid3dweb.EVENT_MOUSE_BUTTON_DOWN, x=pos[0], y=pos[1], button=button, pointer=pointer),
            event(grid3dweb.EVENT_MOUSE_BUTTON_UP, x=pos[0], y=pos[1], button=button, pointer=pointer)]


def pointOn(game, label):
    width, height = game.view3d.width, game.view3d.height
    for button, _ in game.frameButtons():
        if button.text == label and button.cell is None:
            x, y, w, h = scene.buttonRect(button, width, height)
            return (x + w / 2, y + h / 2)
    raise AssertionError("no %r button on screen" % label)


def on3D(game, page, screen="titleScreen"):
    page.on = True
    oneFrame(game, screen)
    assert game.view3d is not None


def setMarks(game, rows, moves):
    for _, (column, row), attribute in scene.CELLS:
        mark = rows[row][column]
        setattr(game, attribute, "" if mark == " " else mark)
    game.moves = moves


# -- the 2D game is untouched while the toggle is off


def test_the_browser_game_is_the_2d_game():
    assert issubclass(WebTicTacToe, tictactoe.TicTacToe)
    # every screen, handler and rule is the 2D game's own
    shared = SCREENS + ["startGame", "restart", "computerTurn", "checkForWinCondition",
                        "drawGrid", "drawGridSlot", "drawButton", "drawQuitButton"]
    shared += [handler for handler, _, _ in scene.CELLS]
    for name in shared:
        assert name not in vars(WebTicTacToe), name


@pytest.mark.parametrize("screen", SCREENS)
def test_nothing_is_sent_and_no_view_opens_while_the_toggle_is_off(game, page, screen):
    setMarks(game, ["XXX", "OO ", "   "], 5)  # an end screen shows while a game has moves
    oneFrame(game, screen)
    assert game.view3d is None
    assert page.opened == 0
    assert page.relay.messages == []


def test_the_2d_canvas_is_still_drawn_on(game, page, monkeypatch):
    drawn = []
    monkeypatch.setattr(game.graphik.graphik, "drawText", lambda *args: drawn.append(args[0]))
    oneFrame(game, "titleScreen")
    assert drawn[0] == "Tic Tac Toe"


# -- switching views


def test_turning_the_toggle_on_opens_the_view_and_sends_the_screen(game, page):
    on3D(game, page)
    assert (game.view3d.width, game.view3d.height) == PHONE
    kinds = [grid3dweb.decode(m)[0] for m in page.relay.messages]
    assert grid3dweb.BOARD in kinds and grid3dweb.HUD in kinds and grid3dweb.VIEW in kinds
    assert hudText(page) == ["Tic Tac Toe", "Start"]


@pytest.mark.parametrize("screen,headline,button", [
    ("titleScreen", "Tic Tac Toe", "Start"),
    ("playerWin", "You won!", "Play Again"),
    ("computerWin", "You lost!", "Play Again"),
    ("tie", "It's a tie!", "Play Again"),
])
def test_every_screen_shows_its_headline_and_buttons_in_3d_without_quit(game, page, screen, headline, button):
    setMarks(game, ["XXX", "OO ", "   "], 5)
    on3D(game, page, screen)
    assert hudText(page) == [headline, button]


def test_the_board_screen_shows_the_marks_as_pieces(game, page):
    setMarks(game, ["X O", " X ", "   "], 3)
    on3D(game, page, "gridScreen")
    # the board's shapes include the X and O pieces; the HUD has no panel
    # (the nine buttons are the tiles themselves)
    built = scene.buildScene(scene.boardCells(game), [], [b for b, _ in game.frameButtons()], *PHONE)
    assert decoded(page, grid3dweb.BOARD)[-1]["shapes"].__len__() == len(built.shapes)
    assert hud(page)["panels"] == []


def test_a_frame_that_did_not_change_is_not_sent_again(game, page):
    on3D(game, page)
    sent = len(page.relay.messages)
    oneFrame(game, "titleScreen")
    assert len(page.relay.messages) == sent


def test_turning_the_toggle_off_closes_the_view_and_the_game_goes_on(game, page):
    on3D(game, page)
    page.on = False
    oneFrame(game, "titleScreen")
    assert game.view3d is None
    assert page.relay.closed


def test_the_view_follows_the_toggle_during_a_pause(game, page):
    # the computer's pause, the end screens' and Start's: the 3D view can be
    # switched on (and is drawn) while the game waits
    oneFrame(game, "gridScreen")
    page.on = True
    asyncio.run(game.pause(1))
    assert game.view3d is not None
    assert decoded(page, grid3dweb.BOARD)


def test_a_pause_ends_on_time_however_slow_the_browser_is(game, page, monkeypatch):
    # each short sleep may come back late in a busy browser; the pause still lasts its second
    now = [0.0]
    slept = []

    def monotonic():
        return now[0]

    async def slowSleep(seconds):
        slept.append(seconds)
        now[0] += 0.3

    monkeypatch.setattr(web.time, "monotonic", monotonic)
    monkeypatch.setattr(tictactoe.asyncio, "sleep", slowSleep)
    asyncio.run(game.pause(1))
    assert len(slept) == 4


def test_the_players_mark_is_sent_before_the_computers_pause(game, page):
    on3D(game, page, "gridScreen")
    before = len(decoded(page, grid3dweb.BOARD))
    game.topLeftL = "X"
    game.drawGrid()
    assert len(decoded(page, grid3dweb.BOARD)) == before + 1


# -- the page starts in 3D (graphik 0.5.1's template)


def test_a_page_that_starts_in_3d_shows_the_first_screen_in_3d_and_takes_the_first_tap(game, page, monkeypatch):
    started = []

    async def startGame():
        started.append(True)

    monkeypatch.setattr(game, "startGame", startGame)
    page.on = True  # before the game has drawn anything: no press on the button
    oneFrame(game, "titleScreen")
    assert game.view3d is not None and page.opened == 1
    assert hudText(page) == ["Tic Tac Toe", "Start"]
    page.relay.events = press(pointOn(game, "Start"), pointer="touch")
    asyncio.run(game.pressButton(game.readEvents()))
    assert started == [True]


# -- the page's 2D/3D button


def test_the_buttons_area_is_read_on_opening_and_on_a_resize(game, page):
    page.area = (330, 8, 52, 36)
    on3D(game, page)
    assert game.keepClear == (330, 8, 52, 36)
    page.area = (780, 8, 52, 36)
    page.relay.events = [event(grid3dweb.EVENT_RESIZED, width=844, height=390)]
    game.readEvents()
    assert game.keepClear == (780, 8, 52, 36)


def test_headlines_and_buttons_keep_out_from_under_the_pages_button(game, page, monkeypatch):
    # a button sitting over the title and Start (wider than any real one), so both must move
    width, height = PHONE
    page.area = (0, 0, width, 480)
    started = []

    async def startGame():
        started.append(True)

    monkeypatch.setattr(game, "startGame", startGame)
    on3D(game, page)
    for label in hud(page)["labels"]:
        assert label["y"] >= 480
    for p in hud(page)["panels"][1:]:  # past the screen's dimming overlay
        assert p["rect"][1] >= 480
    # the press follows Start where it is drawn
    x, y, w, h = scene.buttonRect(game.frameButtons()[0][0], width, height, game.keepClear)
    page.relay.events = press((x + w / 2, y + h / 2))
    asyncio.run(game.pressButton(game.readEvents()))
    assert started == [True]


@pytest.mark.parametrize("screen", ["titleScreen", "playerWin", "computerWin", "tie"])
@pytest.mark.parametrize("size,area", [(PHONE, (330, 8, 52, 36)), (DESKTOP, (1220, 8, 52, 36))])
def test_no_text_runs_under_the_button_where_the_template_puts_it(game, page, screen, size, area):
    setMarks(game, ["XXX", "OO ", "   "], 5)
    page.size_, page.area = size, area
    on3D(game, page, screen)
    ax, ay, aw, ah = area
    for label in hud(page)["labels"]:
        right = label["x"] + label["pixelSize"] * len(label["text"])
        bottom = label["y"] + label["pixelSize"]
        assert right <= ax or label["x"] >= ax + aw or bottom <= ay or label["y"] >= ay + ah


def test_layouts_are_unchanged_when_the_button_is_out_of_the_way():
    title = scene.Button(350, 300, 100, 50, "Start", (0, 0, 0), (255, 255, 255), 20)
    assert scene.buttonRect(title, *PHONE, keepClear=(330, 8, 52, 36)) == scene.buttonRect(title, *PHONE)
    assert scene.headlineLabel("Tic Tac Toe", 400, 150, 64, *PHONE, keepClear=(330, 8, 52, 36)) == \
        scene.headlineLabel("Tic Tac Toe", 400, 150, 64, *PHONE)


# -- presses on the 3D view reach the 2D game's handlers


def test_a_tap_on_start_starts_the_game(game, page, monkeypatch):
    started = []

    async def startGame():
        started.append(True)

    monkeypatch.setattr(game, "startGame", startGame)
    on3D(game, page)
    page.relay.events = press(pointOn(game, "Start"), pointer="touch")
    pressPos = game.readEvents()
    assert isinstance(pressPos, Press3D)
    asyncio.run(game.pressButton(pressPos))
    assert started == [True]


@pytest.mark.parametrize("size", [PHONE, DESKTOP])
@pytest.mark.parametrize("handler,cell,attribute", scene.CELLS)
def test_a_tap_on_a_tile_plays_that_cell(game, page, monkeypatch, handler, cell, attribute, size):
    async def noComputer():
        pass

    monkeypatch.setattr(game, "computerTurn", noComputer)
    page.size_ = size
    on3D(game, page, "gridScreen")
    page.relay.events = press(scene.cellCenterOnScreen(cell, *size), pointer="touch")
    asyncio.run(game.pressButton(game.readEvents()))
    assert getattr(game, attribute) == "X"
    assert game.moves == 1


def test_a_tap_on_an_occupied_tile_or_off_the_board_does_nothing(game, page):
    setMarks(game, ["   ", " O ", "   "], 1)
    on3D(game, page, "gridScreen")
    for pos in (scene.cellCenterOnScreen((1, 1), *PHONE), (3, 3)):
        page.relay.events = press(pos)
        asyncio.run(game.pressButton(game.readEvents()))
    assert game.middleMiddleL == "O" and game.moves == 1


def test_play_again_returns_to_the_title(game, page, monkeypatch):
    shown = []

    async def titleScreen():
        shown.append("title")

    setMarks(game, ["XXX", "OO ", "   "], 5)
    on3D(game, page, "playerWin")
    monkeypatch.setattr(game, "titleScreen", titleScreen)
    page.relay.events = press(pointOn(game, "Play Again"))
    asyncio.run(game.pressButton(game.readEvents()))
    assert shown == ["title"] and game.moves == 0


def test_only_the_left_buttons_press_counts(game, page):
    on3D(game, page)
    page.relay.events = press(pointOn(game, "Start"), button=3)
    assert game.readEvents() is None
    # a release alone (a held button let go) presses nothing either
    page.relay.events = press(pointOn(game, "Start"))[1:]
    assert game.readEvents() is None


def test_a_press_made_during_a_pause_is_discarded_in_3d(game, page):
    on3D(game, page)
    page.relay.events = press(pointOn(game, "Start"))
    game.discardPressesMadeDuringThePause()
    assert game.readEvents() is None


def test_presses_reach_the_2d_canvas_until_the_3d_view_draws():
    page = Page(relayState="loading")
    game = WebTicTacToe(page=page, clock=Clock())
    on3D(game, page)
    page.relay.events = press((10, 10))
    assert game.readEvents() is None
    assert not game.pointerOn3D()


def test_a_press_read_from_3d_does_nothing_once_the_view_is_closed(game, page, monkeypatch):
    started = []

    async def startGame():
        started.append(True)

    monkeypatch.setattr(game, "startGame", startGame)
    on3D(game, page)
    page.relay.events = press(pointOn(game, "Start"))
    pressPos = game.readEvents()
    page.on = False
    game.follow3DToggle()
    asyncio.run(game.pressButton(pressPos))
    assert started == []


# -- hover, resizes


def test_the_mouse_over_a_button_lifts_it(game, page):
    on3D(game, page)
    flat = hud(page)["panels"][-1]["color"]
    page.relay.events = [event(grid3dweb.EVENT_MOUSE_MOTION, x=pointOn(game, "Start")[0], y=pointOn(game, "Start")[1])]
    game.readEvents()
    oneFrame(game, "titleScreen")
    assert hud(page)["panels"][-1]["color"] != flat


def test_the_mouse_over_a_tile_lights_it(game, page):
    on3D(game, page, "gridScreen")
    plain = len(decoded(page, grid3dweb.BOARD)[-1]["shapes"])
    x, y = scene.cellCenterOnScreen((2, 2), *PHONE)
    page.relay.events = [event(grid3dweb.EVENT_MOUSE_MOTION, x=x, y=y)]
    game.readEvents()
    oneFrame(game, "gridScreen")
    assert len(decoded(page, grid3dweb.BOARD)[-1]["shapes"]) > plain


def test_a_touch_leaves_no_hover(game, page):
    on3D(game, page)
    x, y = pointOn(game, "Start")
    page.relay.events = [event(grid3dweb.EVENT_MOUSE_MOTION, x=x, y=y, pointer="touch")] + press((x, y), pointer="touch")
    game.readEvents()
    assert game.pointer3D is None


def test_a_resize_is_followed(game, page, monkeypatch):
    async def noComputer():
        pass

    monkeypatch.setattr(game, "computerTurn", noComputer)
    on3D(game, page, "gridScreen")
    page.relay.events = [event(grid3dweb.EVENT_RESIZED, width=844, height=390)]
    game.readEvents()
    assert (game.view3d.width, game.view3d.height) == (844, 390)
    page.relay.events = press(scene.cellCenterOnScreen((0, 2), 844, 390))
    asyncio.run(game.pressButton(game.readEvents()))
    assert game.bottomLeftL == "X"


# -- a phone held upright


@pytest.mark.parametrize("screen", ["titleScreen", "playerWin", "computerWin", "tie"])
def test_every_label_fits_a_phone_and_is_readable(game, page, screen):
    setMarks(game, ["XXX", "OO ", "   "], 5)
    on3D(game, page, screen)
    width, _ = PHONE
    for label in hud(page)["labels"]:
        assert label["x"] >= 0
        assert label["x"] + label["pixelSize"] * len(label["text"]) <= width
    for button, _ in game.frameButtons():
        x, y, w, h = scene.buttonRect(button, *PHONE)
        assert w >= 44 and h >= 44  # a comfortable tap
        assert scene.buttonPixelSize(button, *PHONE) >= scene.MIN_BUTTON_TEXT


# -- when there is no 3D view


def test_a_view_that_cannot_open_keeps_2d_and_says_why(monkeypatch):
    page = Page(failOpen="WebGL 2 isn't available in this browser")
    game = WebTicTacToe(page=page, clock=Clock())
    drawn = []
    monkeypatch.setattr(game.graphik.graphik, "drawText", lambda text, *args: drawn.append(text))
    page.on = True
    oneFrame(game, "titleScreen")
    assert game.view3d is None
    assert page.toggles == [(False, "WebGL 2 isn't available in this browser")]
    oneFrame(game, "titleScreen")
    assert "No 3D view here: WebGL 2 isn't available in this browser." in drawn
    assert "The 2D view stays." in drawn


def test_a_view_that_fails_while_loading_says_why_and_the_notice_goes(monkeypatch):
    page = Page(relayState="loading")
    clock = Clock()
    game = WebTicTacToe(page=page, clock=clock)
    on3D(game, page)
    page.relay.status = "failed:the 3D engine failed to start"
    page.on = False  # the page's toggle turns itself off on a failure
    drawn = []
    monkeypatch.setattr(game.graphik.graphik, "drawText", lambda text, *args: drawn.append(text))
    oneFrame(game, "titleScreen")
    oneFrame(game, "titleScreen")
    assert game.view3d is None
    assert "No 3D view here: the 3D engine failed to start." in drawn
    drawn.clear()
    clock.now += web.NOTICE_SECONDS + 1
    oneFrame(game, "titleScreen")
    assert drawn and not any(text.startswith("No 3D view") for text in drawn)


def test_a_failure_the_page_closed_itself_still_says_why(monkeypatch):
    # the page closes the relay when it fails (its state is idle again) and keeps the reason
    page = Page(relayState="loading")
    page.unavailable = lambda: "the 3D engine could not be downloaded"
    game = WebTicTacToe(page=page, clock=Clock())
    on3D(game, page)
    page.relay.status = "idle"
    page.on = False
    oneFrame(game, "titleScreen")
    assert game.notice == unavailableLines("the 3D engine could not be downloaded")


def test_a_3d_view_that_failed_before_the_game_began_is_explained_once(monkeypatch):
    page = Page()
    page.unavailable = lambda: "the 3D engine could not be downloaded"
    game = WebTicTacToe(page=page, clock=Clock())
    drawn = []
    monkeypatch.setattr(game.graphik.graphik, "drawText", lambda text, *args: drawn.append(text))
    oneFrame(game, "titleScreen")
    assert game.view3d is None
    assert "No 3D view here: the 3D engine could not be downloaded." in drawn
    game.notice = None
    oneFrame(game, "titleScreen")
    assert game.notice is None


def test_unavailable_lines_are_plain_words():
    assert unavailableLines("no WebGL 2.") == ["No 3D view here: no WebGL 2.", "The 2D view stays."]
    assert unavailableLines("") == ["No 3D view here: it could not load.", "The 2D view stays."]


# -- whole games, played by tapping what the 3D view shows


class GameOver(Exception):
    pass


def tappingPlayer(game, gamesToPlay, results):
    """Taps Start, then the first empty tile, and on an end screen notes its
    headline and taps Play Again, until enough games have ended."""

    def play():
        if game.view3d is None:
            return []
        labels = {button.text for button, _ in game.frameButtons() if button.cell is None}
        if "Play Again" in labels:
            results.append(game.recorder.texts[0][0])
            if len(results) >= gamesToPlay:
                raise GameOver
            return press(pointOn(game, "Play Again"), pointer="touch")
        if "Start" in labels:
            return press(pointOn(game, "Start"), pointer="touch")
        for _, cell, attribute in scene.CELLS:
            if getattr(game, attribute) == "":
                return press(scene.cellCenterOnScreen(cell, game.view3d.width, game.view3d.height),
                             pointer="touch")
        return []

    return play


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_whole_games_are_played_by_tapping_in_3d(game, page, seed):
    tictactoe.random.seed(seed)
    results = []
    page.on = True
    page.relay.player = tappingPlayer(game, 3, results)
    with pytest.raises(GameOver):
        asyncio.run(game.titleScreen())
    assert len(results) == 3
    assert set(results) <= {"You won!", "You lost!", "It's a tie!"}


# -- the browser entry point (src/main.py)


def loadMain(monkeypatch, platform):
    async def titleScreen(self):
        pass

    monkeypatch.setattr(tictactoe.TicTacToe, "titleScreen", titleScreen)
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(web, "BrowserPage", lambda: Page())
    path = tictactoe.__file__.replace("tictactoe.py", "main.py")
    return runpy.run_path(path, run_name="__main__")


def test_the_browser_runs_the_web_game_and_the_desktop_the_2d_one(monkeypatch):
    main = loadMain(monkeypatch, "emscripten")
    assert main["chooseGame"]("emscripten") is WebTicTacToe
    assert main["chooseGame"]("linux") is tictactoe.TicTacToe


def test_a_build_without_the_3d_view_plays_2d(monkeypatch):
    main = loadMain(monkeypatch, "linux")
    monkeypatch.setitem(sys.modules, "strata_view.web", None)
    assert main["chooseGame"]("emscripten") is tictactoe.TicTacToe
