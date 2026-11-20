"""The 3D window runs the 2D game's screens, buttons and rules (feature parity).

StrataTicTacToe is driven through a stand-in for graphik's Grid3DView that
hands out scripted Strata events and keeps every scene it is asked to draw,
so no GPU or Strata library is needed. The last test renders for real and is
skipped wherever Strata can't load.
"""

import asyncio
import os
import types

import pygame
import pytest

pytest.importorskip("preponderous.graphik.grid3d")

import tictactoe  # noqa: E402
from strata_view import StrataUnavailable  # noqa: E402
from strata_view import scene  # noqa: E402
from strata_view.game import StrataTicTacToe, openView  # noqa: E402

# Strata's event types (strata.EVENT_*), so the stand-in needs no binding
STRATA = types.SimpleNamespace(
    EVENT_QUIT=1, EVENT_KEY_DOWN=2, EVENT_KEY_UP=3, EVENT_MOUSE_MOTION=4,
    EVENT_MOUSE_BUTTON_DOWN=5, EVENT_MOUSE_BUTTON_UP=6, EVENT_MOUSE_WHEEL=7,
    EVENT_RESIZED=8, EVENT_TEXT_INPUT=9,
)

SCREENS = ["titleScreen", "gridScreen", "playerWin", "computerWin", "tie"]


class FakeView:
    """Stands in for Grid3DView: events come from `player`, a function that
    is asked for the next batch each time the game polls the window."""

    def __init__(self, player=None, width=800, height=600):
        self.strata = STRATA
        self.width, self.height = width, height
        self.player = player or (lambda game: [])
        self.game = None
        self.scenes = []
        self.closed = False
        self.polls = 0

    def pollEvents(self):
        self.polls += 1
        return list(self.player(self.game))

    def drawScene(self, builtScene, present=True):
        self.scenes.append(builtScene)

    def resize(self, width, height):
        self.width, self.height = width, height

    def close(self):
        self.closed = True


def event(kind, **fields):
    values = dict(button=0, x=0.0, y=0.0, width=0, height=0, scancode=0, repeat=0)
    values.update(fields)
    return types.SimpleNamespace(type=kind, **values)


def click(pos):
    return [event(STRATA.EVENT_MOUSE_BUTTON_DOWN, button=1, x=pos[0], y=pos[1]),
            event(STRATA.EVENT_MOUSE_BUTTON_UP, button=1, x=pos[0], y=pos[1])]


class FrameDrawn(Exception):
    pass


@pytest.fixture(autouse=True)
def noPauses(monkeypatch):
    async def fakeSleep(seconds):
        pass

    monkeypatch.setattr(tictactoe.asyncio, "sleep", fakeSleep)
    monkeypatch.setattr(tictactoe.sys, "platform", "linux")


def make3d(player=None, **size):
    view = FakeView(player, **size)
    game = StrataTicTacToe(view)
    view.game = game
    return game


def oneFrame(game, screen, cls):
    """Runs a screen until its first frame ends; returns that frame's text and buttons."""

    async def drawn(pressPos):
        raise FrameDrawn

    game.endFrame = drawn
    with pytest.raises(FrameDrawn):
        asyncio.run(getattr(cls, screen)(game))
    del game.endFrame
    texts = [call[0] for call in game.graphik.texts] if cls is StrataTicTacToe else None
    buttons = [(text, function.__name__) for _, _, _, _, text, function in game.buttons]
    return texts, buttons


class Recording2DGraphik:
    def __init__(self):
        self.texts = []

    def drawText(self, text, *args):
        self.texts.append(text)

    def drawRectangle(self, *args):
        pass

    def drawButton(self, *args):
        pass


def setMarks(game, rows, moves):
    for _, (column, row), attribute in scene.CELLS:
        mark = rows[row][column]
        setattr(game, attribute, "" if mark == " " else mark)
    game.moves = moves


def pointOn(game, label):
    width, height = game.windowSize
    for button, _ in game.frameButtons():
        if button.text == label and button.cell is None:
            x, y, w, h = scene.buttonRect(button, width, height)
            return (x + w / 2, y + h / 2)
    raise AssertionError("no %r button on screen" % label)


# -- parity: the same screens offer the same text and buttons in both windows

@pytest.mark.parametrize("screen", SCREENS)
def test_each_screen_shows_the_same_text_and_buttons_as_the_2d_window(screen, monkeypatch):
    flat = tictactoe.TicTacToe()
    flat.graphik = Recording2DGraphik()
    monkeypatch.setattr(flat, "readEvents", lambda: None)
    setMarks(flat, ["X O", " X ", "O X"], 5)
    _, flatButtons = oneFrame(flat, screen, tictactoe.TicTacToe)

    deep = make3d()
    setMarks(deep, ["X O", " X ", "O X"], 5)
    deepTexts, deepButtons = oneFrame(deep, screen, StrataTicTacToe)

    assert deepTexts == flat.graphik.texts
    assert deepButtons == flatButtons
    assert deepButtons  # every screen has something to press


def test_the_3d_window_overrides_only_the_window_never_a_screen_or_a_rule():
    # every screen, handler, pause and win check is inherited from TicTacToe unchanged
    shared = SCREENS + ["startGame", "restart", "computerTurn", "checkForWinCondition",
                        "drawGrid", "drawGridSlot", "drawButton", "drawQuitButton"]
    shared += [handler for handler, _, _ in scene.CELLS]
    for name in shared:
        assert name not in vars(StrataTicTacToe), name


def test_neither_window_binds_a_key():
    # The 2D game reads only mouse presses and the window's close; keys do nothing in either
    game = make3d(lambda g: [event(STRATA.EVENT_KEY_DOWN, scancode=code) for code in range(4, 100)])
    assert game.readEvents() is None
    assert not game.view.closed

    flat = tictactoe.TicTacToe()
    keys = [types.SimpleNamespace(type=pygame.KEYDOWN, key=k) for k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_q)]
    original = tictactoe.pygame.event.get
    tictactoe.pygame.event.get = lambda: keys
    try:
        assert flat.readEvents() is None
    finally:
        tictactoe.pygame.event.get = original


# -- presses reach the same handlers

def test_a_press_on_start_starts_the_game(monkeypatch):
    game = make3d()
    oneFrame(game, "titleScreen", StrataTicTacToe)
    started = []

    async def startGame():
        started.append(True)

    monkeypatch.setattr(game, "startGame", startGame)
    oneFrame(game, "titleScreen", StrataTicTacToe)
    asyncio.run(game.pressButton(pointOn(game, "Start")))
    assert started == [True]


@pytest.mark.parametrize("handler,cell,attribute", scene.CELLS)
def test_a_press_on_a_tile_plays_that_cell(handler, cell, attribute, monkeypatch):
    game = make3d()
    oneFrame(game, "gridScreen", StrataTicTacToe)

    async def noComputer():
        pass

    monkeypatch.setattr(game, "computerTurn", noComputer)
    asyncio.run(game.pressButton(scene.cellCenterOnScreen(cell, 800, 600)))
    assert getattr(game, attribute) == "X"
    assert game.moves == 1
    assert sum(1 for _, c, a in scene.CELLS if getattr(game, a) == "X") == 1


def test_a_press_on_an_occupied_tile_or_off_the_board_does_nothing():
    game = make3d()
    setMarks(game, ["   ", " O ", "   "], 1)
    oneFrame(game, "gridScreen", StrataTicTacToe)
    asyncio.run(game.pressButton(scene.cellCenterOnScreen((1, 1), 800, 600)))
    asyncio.run(game.pressButton((4, 4)))
    assert game.middleMiddleL == "O" and game.moves == 1


def test_play_again_and_quit_on_an_end_screen(monkeypatch):
    game = make3d()
    setMarks(game, ["XXX", "OO ", "   "], 5)
    oneFrame(game, "playerWin", StrataTicTacToe)
    shown = []

    async def titleScreen():
        shown.append("title")

    monkeypatch.setattr(game, "titleScreen", titleScreen)
    asyncio.run(game.pressButton(pointOn(game, "Play Again")))
    assert shown == ["title"] and game.moves == 0
    assert all(getattr(game, a) == "" for _, _, a in scene.CELLS)

    setMarks(game, ["XXX", "OO ", "   "], 5)
    oneFrame(game, "playerWin", StrataTicTacToe)
    with pytest.raises(SystemExit):
        asyncio.run(game.pressButton(pointOn(game, "Quit")))
    assert game.view.closed


def test_closing_the_window_quits():
    game = make3d(lambda g: [event(STRATA.EVENT_QUIT)])
    with pytest.raises(SystemExit):
        asyncio.run(game.titleScreen())
    assert game.view.closed


def test_a_press_made_during_a_pause_is_discarded():
    game = make3d(lambda g: click((400, 300)))
    game.discardPressesMadeDuringThePause()
    assert game.pendingPress is None


def test_only_the_left_button_presses():
    game = make3d(lambda g: [event(STRATA.EVENT_MOUSE_BUTTON_DOWN, button=3, x=400, y=300)])
    assert game.readEvents() is None


def test_moving_the_mouse_gives_hover_feedback():
    game = make3d(lambda g: [event(STRATA.EVENT_MOUSE_MOTION, x=12.0, y=34.0)])
    game.readEvents()
    assert game.pointer == (12.0, 34.0)


def test_a_resized_window_resizes_the_view_and_presses_follow_it(monkeypatch):
    game = make3d(lambda g: [event(STRATA.EVENT_RESIZED, width=1280, height=720)])
    game.readEvents()
    assert game.windowSize == (1280, 720)
    game.view.player = lambda g: []
    oneFrame(game, "gridScreen", StrataTicTacToe)

    async def noComputer():
        pass

    monkeypatch.setattr(game, "computerTurn", noComputer)
    asyncio.run(game.pressButton(scene.cellCenterOnScreen((0, 2), 1280, 720)))
    assert game.bottomLeftL == "X"


def test_the_players_mark_is_shown_before_the_computers_pause():
    # drawGrid presents the board straight away in 2D (pygame.display.update); in 3D it draws a frame
    game = make3d()
    oneFrame(game, "gridScreen", StrataTicTacToe)
    drawnBefore = len(game.view.scenes)
    game.drawGrid()
    assert len(game.view.scenes) == drawnBefore + 1


# -- whole games, played by clicking what is on screen

def clickingPlayer(gamesToPlay, results):
    """Clicks Start, then the first empty tile, and on an end screen notes its
    headline and clicks Play Again, or Quit once enough games have ended."""

    def play(game):
        labels = {button.text for button, _ in game.frameButtons() if button.cell is None}
        if "Play Again" in labels:
            results.append(game.graphik.texts[0][0])
            return click(pointOn(game, "Quit" if len(results) >= gamesToPlay else "Play Again"))
        if "Start" in labels:
            return click(pointOn(game, "Start"))
        width, height = game.windowSize
        for _, cell, attribute in scene.CELLS:
            if getattr(game, attribute) == "":
                return click(scene.cellCenterOnScreen(cell, width, height))
        return []

    return play


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_whole_games_are_played_and_quit_by_clicking(seed):
    tictactoe.random.seed(seed)
    results = []
    game = make3d(clickingPlayer(3, results))
    with pytest.raises(SystemExit):
        asyncio.run(game.titleScreen())
    assert len(results) == 3
    assert set(results) <= {"You won!", "You lost!", "It's a tie!"}
    assert game.view.closed


# -- the interface choice and fallback (tictactoe.main)

def test_open_view_reports_a_missing_strata_in_plain_words(monkeypatch):
    import preponderous.graphik.grid3d as grid3d

    def unavailable(*args, **kwargs):
        raise grid3d.Unavailable("the strata-engine package isn't installed")

    monkeypatch.setattr(grid3d.Grid3DView, "open", unavailable)
    with pytest.raises(StrataUnavailable, match="strata-engine"):
        openView()


def test_a_real_strata_frame_renders(tmp_path):
    if os.environ.get("TICTAKTOE_SKIP_STRATA_RENDER"):
        pytest.skip("TICTAKTOE_SKIP_STRATA_RENDER is set")
    try:
        view = openView(320, 240, window=False)
    except StrataUnavailable as reason:
        pytest.skip("Strata can't run here: %s" % reason)
    try:
        game = StrataTicTacToe(view)
        setMarks(game, ["X O", " X ", "O  "], 4)
        oneFrame(game, "gridScreen", StrataTicTacToe)
        game.render()
        path = tmp_path / "frame.png"
        view.savePng(str(path))
        assert path.stat().st_size > 1000
    finally:
        view.close()
