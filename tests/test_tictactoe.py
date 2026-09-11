import types

import pygame
import pytest

import tictactoe


#  Every cell of the board, paired with the handler that claims it for the player.
CELLS = [
    ("topLeft", "topLeftL"),
    ("topMiddle", "topMiddleL"),
    ("topRight", "topRightL"),
    ("middleLeft", "middleLeftL"),
    ("middleMiddle", "middleMiddleL"),
    ("middleRight", "middleRightL"),
    ("bottomLeft", "bottomLeftL"),
    ("bottomMiddle", "bottomMiddleL"),
    ("bottomRight", "bottomRightL"),
]

CELL_ATTRIBUTES = [attribute for _, attribute in CELLS]

#  The eight lines checkForWinCondition tests, in the order the source checks them.
WIN_LINES = [
    ("top row", ("topLeftL", "topMiddleL", "topRightL")),
    ("middle row", ("middleLeftL", "middleMiddleL", "middleRightL")),
    ("bottom row", ("bottomLeftL", "bottomMiddleL", "bottomRightL")),
    ("left column", ("topLeftL", "middleLeftL", "bottomLeftL")),
    ("middle column", ("topMiddleL", "middleMiddleL", "bottomMiddleL")),
    ("right column", ("topRightL", "middleRightL", "bottomRightL")),
    ("diagonal ->", ("topLeftL", "middleMiddleL", "bottomRightL")),
    ("diagonal <-", ("topRightL", "middleMiddleL", "bottomLeftL")),
]

#  The three end-of-game screens, paired with the headline each one draws.
END_SCREENS = [
    ("playerWin", "You won!"),
    ("computerWin", "You lost!"),
    ("tie", "It's a tie!"),
]

#  Every screen that offers a Quit button, paired with the handler behind each of its buttons.
BUTTON_SCREENS = [
    ("playerWin", {"Play Again": "restart", "Quit": "exit"}),
    ("computerWin", {"Play Again": "restart", "Quit": "exit"}),
    ("tie", {"Play Again": "restart", "Quit": "exit"}),
    ("titleScreen", {"Start": "gridScreen", "Quit": "exit"}),
]


class ScreenLoopExit(Exception):
    pass


#  Stands in for Graphik so a screen's draw calls can be asserted without rendering anything.
class RecordingGraphik:
    def __init__(self):
        self.calls = []

    def drawRectangle(self, xpos, ypos, width, height, color):
        self.calls.append(("drawRectangle",))

    def drawText(self, text, xpos, ypos, size, color):
        self.calls.append(("drawText", text))

    def drawButton(self, xpos, ypos, width, height, colorBox, colorText, sizeText, text, function):
        self.calls.append(("drawButton", text, function))


@pytest.fixture
def game(monkeypatch):
    #  The three end-of-game screens and the title screen loop forever in production, and
    #  computerTurn sleeps a second per move, so each is replaced with a recorder. Drawing is
    #  suppressed as well: the state machine under test is what these tests are about.
    monkeypatch.setattr(tictactoe.time, "sleep", lambda seconds: None)

    ticTacToe = tictactoe.TicTacToe()
    ticTacToe.screensShown = []
    ticTacToe.drawGrid = lambda: None
    ticTacToe.playerWin = lambda: ticTacToe.screensShown.append("playerWin")
    ticTacToe.computerWin = lambda: ticTacToe.screensShown.append("computerWin")
    ticTacToe.tie = lambda: ticTacToe.screensShown.append("tie")
    ticTacToe.titleScreen = lambda: ticTacToe.screensShown.append("titleScreen")
    return ticTacToe


def readBoard(ticTacToe):
    return {attribute: getattr(ticTacToe, attribute) for attribute in CELL_ATTRIBUTES}


def setBoard(ticTacToe, letters):
    for attribute, letter in zip(CELL_ATTRIBUTES, letters):
        setattr(ticTacToe, attribute, letter)
    ticTacToe.moves = len([letter for letter in letters if letter != ""])


def renderOneFrame(ticTacToe, monkeypatch, screenName):
    #  Every screen loops forever over pygame.event.get(), so the event queue is replaced with
    #  one that yields a single non-QUIT event and then breaks the loop from the inside. The
    #  screen is looked up on the class because the fixture replaces it on the instance.
    framesRendered = []

    def fakeEventGet():
        if framesRendered:
            raise ScreenLoopExit()
        framesRendered.append(1)
        return [types.SimpleNamespace(type=pygame.MOUSEMOTION)]

    monkeypatch.setattr(tictactoe.pygame.event, "get", fakeEventGet)
    ticTacToe.graphik = RecordingGraphik()
    ticTacToe.moves = 9

    with pytest.raises(ScreenLoopExit):
        getattr(tictactoe.TicTacToe, screenName)(ticTacToe)

    return ticTacToe.graphik.calls


def test_new_game_starts_with_an_empty_board(game):
    assert readBoard(game) == {attribute: "" for attribute in CELL_ATTRIBUTES}
    assert game.moves == 0


@pytest.mark.parametrize("handlerName,attributeName", CELLS)
def test_handler_marks_only_its_own_cell(game, handlerName, attributeName):
    stepsTaken = []
    game.drawGrid = lambda: stepsTaken.append("drawGrid")
    game.computerTurn = lambda: stepsTaken.append("computerTurn")

    getattr(game, handlerName)()

    expected = {attribute: "" for attribute in CELL_ATTRIBUTES}
    expected[attributeName] = "X"
    assert readBoard(game) == expected
    assert game.moves == 1
    assert stepsTaken == ["drawGrid", "computerTurn"]


@pytest.mark.parametrize("handlerName,attributeName", CELLS)
def test_handler_ignores_an_occupied_cell(game, handlerName, attributeName):
    stepsTaken = []
    game.drawGrid = lambda: stepsTaken.append("drawGrid")
    game.computerTurn = lambda: stepsTaken.append("computerTurn")
    setattr(game, attributeName, "O")
    game.moves = 1

    getattr(game, handlerName)()

    assert getattr(game, attributeName) == "O"
    assert game.moves == 1
    assert stepsTaken == []


@pytest.mark.parametrize("lineName,attributes", WIN_LINES)
def test_player_line_shows_the_player_win_screen(game, lineName, attributes):
    for attribute in attributes:
        setattr(game, attribute, "X")

    game.checkForWinCondition()

    assert game.screensShown == ["playerWin"]


@pytest.mark.parametrize("lineName,attributes", WIN_LINES)
def test_computer_line_shows_the_computer_win_screen(game, lineName, attributes):
    for attribute in attributes:
        setattr(game, attribute, "O")

    game.checkForWinCondition()

    assert game.screensShown == ["computerWin"]


def test_unfinished_board_shows_no_screen(game):
    setBoard(game, ["X", "O", "", "", "X", "", "", "", "O"])

    game.checkForWinCondition()

    assert game.screensShown == []


def test_full_board_without_a_line_shows_the_tie_screen(game):
    setBoard(game, ["X", "O", "X", "X", "O", "O", "O", "X", "X"])

    game.checkForWinCondition()

    assert game.moves == 9
    assert game.screensShown == ["tie"]


def test_win_check_keeps_checking_after_a_win_is_found(game):
    #  checkForWinCondition has no early return, so a winning line on a full board reaches the
    #  moves == 9 tie branch as well. In production this is unobservable because playerWin never
    #  returns; the recorders in this fixture make the control flow visible. Current behavior.
    setBoard(game, ["X", "X", "X", "O", "O", "X", "X", "O", "O"])

    game.checkForWinCondition()

    assert game.screensShown == ["playerWin", "tie"]


def test_restart_clears_the_board_and_returns_to_the_title_screen(game):
    setBoard(game, ["X", "O", "X", "X", "O", "O", "O", "X", "X"])

    game.restart()

    assert readBoard(game) == {attribute: "" for attribute in CELL_ATTRIBUTES}
    assert game.moves == 0
    assert game.screensShown == ["titleScreen"]


def test_computer_turn_takes_the_last_empty_cell(game):
    setBoard(game, ["X", "O", "X", "X", "O", "O", "O", "X", ""])

    game.computerTurn()

    assert game.bottomRightL == "O"
    assert game.moves == 9
    assert game.screensShown == ["tie"]


def test_computer_turn_does_not_move_on_a_full_board(game):
    setBoard(game, ["X", "O", "X", "X", "O", "O", "O", "X", "X"])
    boardBefore = readBoard(game)

    game.computerTurn()

    assert readBoard(game) == boardBefore
    assert game.moves == 9


@pytest.mark.parametrize("screenName,headline", END_SCREENS)
def test_end_screen_draws_its_own_headline(game, monkeypatch, screenName, headline):
    calls = renderOneFrame(game, monkeypatch, screenName)

    assert [call[1] for call in calls if call[0] == "drawText"] == [headline]


@pytest.mark.parametrize("screenName,handlerNames", BUTTON_SCREENS)
def test_screen_buttons_call_the_game_methods(game, monkeypatch, screenName, handlerNames):
    calls = renderOneFrame(game, monkeypatch, screenName)

    buttons = {call[1]: call[2] for call in calls if call[0] == "drawButton"}
    expected = {label: getattr(game, handlerName) for label, handlerName in handlerNames.items()}
    assert buttons == expected
