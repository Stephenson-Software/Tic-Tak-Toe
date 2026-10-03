import asyncio
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
        self.calls.append(("drawRectangle", xpos, ypos, width, height))

    def drawText(self, text, xpos, ypos, size, color):
        self.calls.append(("drawText", text))

    def drawButton(self, xpos, ypos, width, height, colorBox, colorText, sizeText, text, function):
        self.calls.append(("drawButton", text, function, width, sizeText, xpos, ypos, height))


class Finished:
    #  An awaitable that is already done.
    def __await__(self):
        return iter(())


def recorder(log, name):
    #  A stand-in for a screen or handler. Its name is recorded as soon as it is called, so a
    #  call whose result is never awaited (as from Graphik.drawButton) is still caught.
    def record():
        log.append(name)
        return Finished()
    return record


@pytest.fixture
def pauses(monkeypatch):
    #  Every asyncio.sleep the game awaits, by duration. Nothing actually waits: computerTurn and
    #  the end screens pause a second each, and every frame yields with asyncio.sleep(0).
    recorded = []

    async def fakeSleep(seconds):
        recorded.append(seconds)

    monkeypatch.setattr(tictactoe.asyncio, "sleep", fakeSleep)
    return recorded


@pytest.fixture
def game(monkeypatch, pauses):
    #  The three end-of-game screens and the title screen loop forever in production, so each is
    #  replaced with a recorder. Drawing is suppressed as well: the state machine under test is
    #  what these tests are about.
    monkeypatch.setattr(tictactoe.sys, "platform", "linux")

    ticTacToe = tictactoe.TicTacToe()
    ticTacToe.screensShown = []
    ticTacToe.drawGrid = lambda: None
    ticTacToe.playerWin = recorder(ticTacToe.screensShown, "playerWin")
    ticTacToe.computerWin = recorder(ticTacToe.screensShown, "computerWin")
    ticTacToe.tie = recorder(ticTacToe.screensShown, "tie")
    ticTacToe.titleScreen = recorder(ticTacToe.screensShown, "titleScreen")
    return ticTacToe


def readBoard(ticTacToe):
    return {attribute: getattr(ticTacToe, attribute) for attribute in CELL_ATTRIBUTES}


def setBoard(ticTacToe, letters):
    for attribute, letter in zip(CELL_ATTRIBUTES, letters):
        setattr(ticTacToe, attribute, letter)
    ticTacToe.moves = len([letter for letter in letters if letter != ""])


def runScreen(ticTacToe, monkeypatch, screenName, eventBatches):
    #  Every screen loops forever, reading pygame.event.get() once per frame, so the event queue
    #  is replaced with one that hands out the given batches, one per frame, and then breaks the
    #  loop from the inside. The screen is looked up on the class because the fixture replaces
    #  it on the instance.
    eventBatches = list(eventBatches)

    def fakeEventGet():
        if not eventBatches:
            raise ScreenLoopExit()
        return eventBatches.pop(0)

    monkeypatch.setattr(tictactoe.pygame.event, "get", fakeEventGet)
    ticTacToe.graphik = RecordingGraphik()
    ticTacToe.moves = 9

    with pytest.raises(ScreenLoopExit):
        asyncio.run(getattr(tictactoe.TicTacToe, screenName)(ticTacToe))

    return ticTacToe.graphik.calls


def renderOneFrame(ticTacToe, monkeypatch, screenName):
    #  One frame with a single non-QUIT event, after which the loop is broken.
    return runScreen(ticTacToe, monkeypatch, screenName, [[types.SimpleNamespace(type=pygame.MOUSEMOTION)]])


def press(pos, button=1):
    return types.SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, pos=pos, button=button)


def release(pos, button=1):
    return types.SimpleNamespace(type=pygame.MOUSEBUTTONUP, pos=pos, button=button)


def buttonCentre(ticTacToe, label):
    #  The centre of the button drawn with the given label in the last frame.
    for xpos, ypos, width, height, text, _ in ticTacToe.buttons:
        if text == label:
            return (xpos + width // 2, ypos + height // 2)
    raise AssertionError("no button labelled " + repr(label))


def frameButtons(ticTacToe):
    #  The last frame's buttons, by label, mapped to the handler a press on each one awaits.
    return {text: function for _, _, _, _, text, function in ticTacToe.buttons}


def test_new_game_starts_with_an_empty_board(game):
    assert readBoard(game) == {attribute: "" for attribute in CELL_ATTRIBUTES}
    assert game.moves == 0


@pytest.mark.parametrize("handlerName,attributeName", CELLS)
def test_handler_marks_only_its_own_cell(game, handlerName, attributeName):
    stepsTaken = []
    game.drawGrid = lambda: stepsTaken.append("drawGrid")
    game.computerTurn = recorder(stepsTaken, "computerTurn")

    asyncio.run(getattr(game, handlerName)())

    expected = {attribute: "" for attribute in CELL_ATTRIBUTES}
    expected[attributeName] = "X"
    assert readBoard(game) == expected
    assert game.moves == 1
    assert stepsTaken == ["drawGrid", "computerTurn"]


@pytest.mark.parametrize("handlerName,attributeName", CELLS)
def test_handler_ignores_an_occupied_cell(game, handlerName, attributeName):
    stepsTaken = []
    game.drawGrid = lambda: stepsTaken.append("drawGrid")
    game.computerTurn = recorder(stepsTaken, "computerTurn")
    setattr(game, attributeName, "O")
    game.moves = 1

    asyncio.run(getattr(game, handlerName)())

    assert getattr(game, attributeName) == "O"
    assert game.moves == 1
    assert stepsTaken == []


@pytest.mark.parametrize("lineName,attributes", WIN_LINES)
def test_player_line_shows_the_player_win_screen(game, lineName, attributes):
    for attribute in attributes:
        setattr(game, attribute, "X")

    asyncio.run(game.checkForWinCondition())

    assert game.screensShown == ["playerWin"]


@pytest.mark.parametrize("lineName,attributes", WIN_LINES)
def test_computer_line_shows_the_computer_win_screen(game, lineName, attributes):
    for attribute in attributes:
        setattr(game, attribute, "O")

    asyncio.run(game.checkForWinCondition())

    assert game.screensShown == ["computerWin"]


def test_unfinished_board_shows_no_screen(game):
    setBoard(game, ["X", "O", "", "", "X", "", "", "", "O"])

    asyncio.run(game.checkForWinCondition())

    assert game.screensShown == []


def test_full_board_without_a_line_shows_the_tie_screen(game):
    setBoard(game, ["X", "O", "X", "X", "O", "O", "O", "X", "X"])

    asyncio.run(game.checkForWinCondition())

    assert game.moves == 9
    assert game.screensShown == ["tie"]


def test_win_check_keeps_checking_after_a_win_is_found(game):
    #  checkForWinCondition has no early return, so a winning line on a full board reaches the
    #  moves == 9 tie branch as well. In production this is unobservable because playerWin never
    #  returns; the recorders in this fixture make the control flow visible. Current behavior.
    setBoard(game, ["X", "X", "X", "O", "O", "X", "X", "O", "O"])

    asyncio.run(game.checkForWinCondition())

    assert game.screensShown == ["playerWin", "tie"]


def test_restart_clears_the_board_and_returns_to_the_title_screen(game):
    setBoard(game, ["X", "O", "X", "X", "O", "O", "O", "X", "X"])

    asyncio.run(game.restart())

    assert readBoard(game) == {attribute: "" for attribute in CELL_ATTRIBUTES}
    assert game.moves == 0
    assert game.screensShown == ["titleScreen"]


def test_computer_turn_takes_the_last_empty_cell(game):
    setBoard(game, ["X", "O", "X", "X", "O", "O", "O", "X", ""])

    asyncio.run(game.computerTurn())

    assert game.bottomRightL == "O"
    assert game.moves == 9
    assert game.screensShown == ["tie"]


@pytest.mark.parametrize("roll,attributeName", list(enumerate(CELL_ATTRIBUTES, start=1)))
def test_computer_roll_claims_its_own_cell(game, monkeypatch, roll, attributeName):
    monkeypatch.setattr(tictactoe.random, "randint", lambda low, high: roll)

    asyncio.run(game.computerTurn())

    expected = {attribute: "" for attribute in CELL_ATTRIBUTES}
    expected[attributeName] = "O"
    assert readBoard(game) == expected
    assert game.moves == 1


def test_computer_turn_rolls_again_on_a_ten_or_an_occupied_cell(game, monkeypatch):
    #  randint(1, 10) can roll a 10, which no cell answers to, so the loop simply rolls again.
    #  Current behavior: a wasted roll, not a skipped turn.
    rolls = [10, 1, 2]
    monkeypatch.setattr(tictactoe.random, "randint", lambda low, high: rolls.pop(0))
    setBoard(game, ["X", "", "", "", "", "", "", "", ""])

    asyncio.run(game.computerTurn())

    assert rolls == []
    assert game.topLeftL == "X"
    assert game.topMiddleL == "O"
    assert game.moves == 2


def test_computer_turn_does_not_move_on_a_full_board(game):
    setBoard(game, ["X", "O", "X", "X", "O", "O", "O", "X", "X"])
    boardBefore = readBoard(game)

    asyncio.run(game.computerTurn())

    assert readBoard(game) == boardBefore
    assert game.moves == 9


@pytest.mark.parametrize("screenName,headline", END_SCREENS)
def test_end_screen_draws_its_own_headline(game, monkeypatch, screenName, headline):
    calls = renderOneFrame(game, monkeypatch, screenName)

    assert [call[1] for call in calls if call[0] == "drawText"] == [headline]


@pytest.mark.parametrize("screenName,handlerNames", BUTTON_SCREENS)
def test_screen_buttons_call_the_game_methods(game, monkeypatch, screenName, handlerNames):
    renderOneFrame(game, monkeypatch, screenName)

    buttons = frameButtons(game)
    expected = {label: getattr(game, handlerName) for label, handlerName in handlerNames.items()}
    assert buttons == expected


@pytest.mark.parametrize("screenName", [screenName for screenName, _ in BUTTON_SCREENS])
def test_screen_button_labels_fit_inside_their_buttons(game, monkeypatch, screenName):
    #  Issue #23: "Play Again" at size 20 is 104 px wide in the font Graphik draws with, which
    #  spilled past the 100 px button on the lost and tie screens. Measured with the real font.
    calls = renderOneFrame(game, monkeypatch, screenName)

    for call in calls:
        if call[0] == "drawButton":
            text, width, sizeText = call[1], call[3], call[4]
            assert pygame.font.Font("freesansbold.ttf", sizeText).size(text)[0] <= width, text


def test_end_screens_draw_their_buttons_at_the_same_sizes(game, monkeypatch):
    buttonSizes = []
    for screenName, _ in END_SCREENS:
        calls = renderOneFrame(game, monkeypatch, screenName)
        buttonSizes.append([(call[1], call[3], call[4]) for call in calls if call[0] == "drawButton"])

    assert buttonSizes[0] == buttonSizes[1] == buttonSizes[2]


def drawBoard(ticTacToe):
    #  The fixture replaces drawGrid on the instance, so the real one is looked up on the class.
    ticTacToe.graphik = RecordingGraphik()
    ticTacToe.buttons = []
    tictactoe.TicTacToe.drawGrid(ticTacToe)
    return ticTacToe.graphik.calls


def test_grid_slot_shows_its_cell_and_calls_its_handler(game):
    #  A distinct letter per cell makes a slot wired to the wrong attribute show up by value.
    for attribute, letter in zip(CELL_ATTRIBUTES, "ABCDEFGHI"):
        setattr(game, attribute, letter)

    drawBoard(game)

    slots = [(text, function) for _, _, _, _, text, function in game.buttons]
    assert slots == [(getattr(game, attribute), getattr(game, handlerName)) for handlerName, attribute in CELLS]


def test_grid_slots_form_a_three_by_three_grid_inside_the_board(game):
    calls = drawBoard(game)

    board = [call for call in calls if call[0] == "drawRectangle"]
    assert len(board) == 1
    _, boardX, boardY, boardWidth, boardHeight = board[0]

    slots = [call for call in calls if call[0] == "drawButton"]
    positions = [(call[5], call[6]) for call in slots]
    assert all((call[3], call[7]) == (100, 100) for call in slots)

    #  Row-major order, 125 px apart, with the middle slot centred on the display.
    columns = sorted(set(x for x, _ in positions))
    rows = sorted(set(y for _, y in positions))
    assert positions == [(x, y) for y in rows for x in columns]
    assert [b - a for a, b in zip(columns, columns[1:])] == [125, 125]
    assert [b - a for a, b in zip(rows, rows[1:])] == [125, 125]
    assert (columns[1] + 50, rows[1] + 50) == (game.displayWidth // 2, game.displayHeight // 2)

    for x, y in positions:
        assert boardX <= x and x + 100 <= boardX + boardWidth
        assert boardY <= y and y + 100 <= boardY + boardHeight


#  Every screen that runs its own event loop, and so must handle the window being closed.
LOOPING_SCREENS = ["titleScreen", "gridScreen", "playerWin", "computerWin", "tie"]


def recordShutdown(monkeypatch):
    #  quit() is looked up as a module global before the builtin, so it can be replaced on the
    #  module. It raises to stand in for the interpreter exiting, which also ends the loop.
    shutdown = []

    def fakeQuit():
        shutdown.append("quit")
        raise ScreenLoopExit()

    monkeypatch.setattr(tictactoe.pygame, "quit", lambda: shutdown.append("pygame.quit"))
    monkeypatch.setattr(tictactoe, "quit", fakeQuit, raising=False)
    return shutdown


@pytest.mark.parametrize("screenName", LOOPING_SCREENS)
def test_closing_the_window_shuts_pygame_down_and_quits(game, monkeypatch, screenName):
    shutdown = recordShutdown(monkeypatch)
    monkeypatch.setattr(tictactoe.pygame.event, "get", lambda: [types.SimpleNamespace(type=pygame.QUIT)])
    game.moves = 9

    with pytest.raises(ScreenLoopExit):
        asyncio.run(getattr(tictactoe.TicTacToe, screenName)(game))

    assert shutdown == ["pygame.quit", "quit"]


def test_exit_shuts_pygame_down_and_quits(game, monkeypatch):
    shutdown = recordShutdown(monkeypatch)

    with pytest.raises(ScreenLoopExit):
        asyncio.run(game.exit())

    assert shutdown == ["pygame.quit", "quit"]


def test_grid_screen_redraws_the_board_once_per_frame(game, monkeypatch):
    #  Drawing happens once per frame, whatever the events: a frame with no events still draws
    #  the board (the browser build shows nothing otherwise), and a frame with three events
    #  draws it once.
    eventBatches = [[], [types.SimpleNamespace(type=pygame.MOUSEMOTION)] * 3]

    def fakeEventGet():
        if not eventBatches:
            raise ScreenLoopExit()
        return eventBatches.pop(0)

    draws = []
    monkeypatch.setattr(tictactoe.pygame.event, "get", fakeEventGet)
    game.gameDisplay = types.SimpleNamespace(fill=lambda color: draws.append(("fill", color)))
    game.drawGrid = lambda: draws.append("drawGrid")

    with pytest.raises(ScreenLoopExit):
        asyncio.run(tictactoe.TicTacToe.gridScreen(game))

    assert draws == [("fill", game.white), "drawGrid"] * 2


@pytest.mark.parametrize("screenName", LOOPING_SCREENS)
def test_every_frame_yields_to_the_event_loop(game, monkeypatch, pauses, screenName):
    #  The browser build (pygbag) freezes unless every frame hands control back to the browser.
    runScreen(game, monkeypatch, screenName, [[], [], []])

    assert pauses.count(0) == 3


@pytest.mark.parametrize("screenName", [screenName for screenName, _ in END_SCREENS])
def test_end_screen_pauses_a_second_before_it_shows(game, monkeypatch, pauses, screenName):
    renderOneFrame(game, monkeypatch, screenName)

    assert pauses[0] == 1


def test_computer_pauses_a_second_before_it_moves(game, pauses):
    asyncio.run(game.computerTurn())

    assert pauses == [1]
    assert game.moves == 1


@pytest.mark.parametrize("screenName,handlerNames", BUTTON_SCREENS)
def test_a_tap_presses_the_button_it_lands_on_once(game, monkeypatch, screenName, handlerNames):
    #  A browser tap delivers its press and its release in the same frame, by which time the
    #  button is no longer held, so the press event is what presses a button.
    for label, handlerName in handlerNames.items():
        pressed = []
        setattr(game, handlerName, recorder(pressed, handlerName))
        renderOneFrame(game, monkeypatch, screenName)
        centre = buttonCentre(game, label)

        runScreen(game, monkeypatch, screenName, [[press(centre), release(centre)], [], []])

        assert pressed == [handlerName], label


@pytest.mark.parametrize("screenName,handlerNames", BUTTON_SCREENS)
def test_a_held_button_presses_nothing_further(game, monkeypatch, screenName, handlerNames):
    #  Graphik.drawButton fires on every frame the left button is held over the box; the game
    #  hands it a no-op, so frames without a press event press nothing, held or not.
    pressed = []
    for handlerName in handlerNames.values():
        setattr(game, handlerName, recorder(pressed, handlerName))
    renderOneFrame(game, monkeypatch, screenName)
    centres = [buttonCentre(game, label) for label in handlerNames]
    game.graphik = tictactoe.Graphik(game.gameDisplay)
    monkeypatch.setattr(tictactoe.pygame.mouse, "get_pressed", lambda *args, **kwargs: (1, 0, 0))

    for centre in centres:
        monkeypatch.setattr(tictactoe.pygame.mouse, "get_pos", lambda centre=centre: centre)
        eventBatches = [[], []]
        monkeypatch.setattr(tictactoe.pygame.event, "get", lambda: eventBatches.pop(0) if eventBatches else (_ for _ in ()).throw(ScreenLoopExit()))
        with pytest.raises(ScreenLoopExit):
            asyncio.run(getattr(tictactoe.TicTacToe, screenName)(game))

    assert pressed == []


@pytest.mark.parametrize("screenName,handlerNames", BUTTON_SCREENS)
def test_a_right_press_or_a_press_beside_the_buttons_presses_nothing(game, monkeypatch, screenName, handlerNames):
    pressed = []
    for handlerName in handlerNames.values():
        setattr(game, handlerName, recorder(pressed, handlerName))
    renderOneFrame(game, monkeypatch, screenName)
    centre = buttonCentre(game, "Quit")

    runScreen(game, monkeypatch, screenName, [[press(centre, button=3)], [press((5, 5))], []])

    assert pressed == []


@pytest.mark.parametrize("handlerName,attributeName", CELLS)
def test_a_tap_on_a_cell_claims_it(game, monkeypatch, handlerName, attributeName):
    game.drawGrid = tictactoe.TicTacToe.drawGrid.__get__(game)
    game.computerTurn = recorder([], "computerTurn")
    drawBoard(game)
    slot = [(xpos + 50, ypos + 50) for xpos, ypos, _, _, _, function in game.buttons if function == getattr(game, handlerName)][0]
    game.moves = 0

    eventBatches = [[press(slot), release(slot)], []]

    def fakeEventGet():
        if not eventBatches:
            raise ScreenLoopExit()
        return eventBatches.pop(0)

    monkeypatch.setattr(tictactoe.pygame.event, "get", fakeEventGet)
    with pytest.raises(ScreenLoopExit):
        asyncio.run(tictactoe.TicTacToe.gridScreen(game))

    expected = {attribute: "" for attribute in CELL_ATTRIBUTES}
    expected[attributeName] = "X"
    assert readBoard(game) == expected


@pytest.mark.parametrize("screenName", [screenName for screenName, _ in BUTTON_SCREENS])
def test_the_browser_build_offers_no_quit_button(game, monkeypatch, screenName):
    #  A browser tab has nothing to quit to, so under pygbag the screens draw no Quit button.
    monkeypatch.setattr(tictactoe.sys, "platform", "emscripten")

    renderOneFrame(game, monkeypatch, screenName)

    assert "Quit" not in frameButtons(game)
    assert len(frameButtons(game)) == 1


def test_the_browser_build_seeds_the_computer_from_the_clock(monkeypatch):
    #  Every page load would otherwise start from the same random state.
    seeds = []
    monkeypatch.setattr(tictactoe.sys, "platform", "emscripten")
    monkeypatch.setattr(tictactoe.random, "seed", lambda value=None: seeds.append(value))

    tictactoe.TicTacToe()

    assert len(seeds) == 1 and isinstance(seeds[0], int)


@pytest.mark.parametrize("screenName", [screenName for screenName, _ in END_SCREENS])
def test_end_screen_discards_presses_made_during_its_pause(game, monkeypatch, pauses, screenName):
    #  A tap made during the pause was aimed at the board, which is still shown, so it must not
    #  press the end screen's Play Again button, which covers the bottom-middle cell.
    steps = []
    monkeypatch.setattr(tictactoe.pygame.event, "clear", lambda eventtype=None: steps.append(("clear", eventtype)))
    original = tictactoe.asyncio.sleep

    async def recordPause(seconds):
        steps.append(("sleep", seconds))
        await original(seconds)

    monkeypatch.setattr(tictactoe.asyncio, "sleep", recordPause)

    renderOneFrame(game, monkeypatch, screenName)

    assert steps[:2] == [("sleep", 1), ("clear", (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))]


def test_play_again_covers_the_bottom_middle_cell(game, monkeypatch):
    #  The overlap the discarded presses guard against.
    drawBoard(game)
    cell = [(xpos + 50, ypos + 50) for xpos, ypos, _, _, _, function in game.buttons if function == game.bottomMiddle][0]
    renderOneFrame(game, monkeypatch, "playerWin")

    assert any(tictactoe.pressLandedOn(cell, xpos, ypos, width, height)
               for xpos, ypos, width, height, text, _ in game.buttons if text == "Play Again")
