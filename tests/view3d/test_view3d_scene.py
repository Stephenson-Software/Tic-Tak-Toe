"""The 3D view's state-to-scene mapping and picking (src/strata_view/scene.py).

These need no GPU and no Strata: buildScene() returns plain shapes. They need
graphik's 3D grid view (preponderous.graphik.grid3d) and are skipped where the
installed graphik predates it.
"""

import pytest

pytest.importorskip("preponderous.graphik.grid3d")

from preponderous.graphik import Graphik  # noqa: E402
from preponderous.graphik.grid3d import CYLINDER  # noqa: E402

import tictactoe  # noqa: E402
from strata_view import scene  # noqa: E402

SIZES = [(800, 600), (1280, 720), (600, 800)]


def emptyCells():
    return {cell: "" for _, cell, _ in scene.CELLS}


def button(text="Quit", xpos=350, ypos=500, width=100, height=50, cell=None):
    return scene.Button(xpos, ypos, width, height, text, (0, 0, 0), (255, 255, 255), 20, cell)


def test_every_cell_names_a_real_handler_and_attribute():
    game = tictactoe.TicTacToe
    handlers = [handler for handler, _, _ in scene.CELLS]
    cells = [cell for _, cell, _ in scene.CELLS]
    assert len(set(handlers)) == len(set(cells)) == 9
    for handler, _, attribute in scene.CELLS:
        assert callable(getattr(game, handler))
        assert hasattr(tictactoe.TicTacToe(), attribute)


@pytest.mark.parametrize("width,height", SIZES)
def test_a_press_on_each_tile_picks_that_cell(width, height):
    for _, cell, _ in scene.CELLS:
        centre = scene.cellCenterOnScreen(cell, width, height)
        assert scene.pickCell(centre, width, height) == cell


@pytest.mark.parametrize("width,height", SIZES)
def test_the_board_is_drawn_the_way_round_the_2d_grid_is(width, height):
    # top row furthest away (higher on screen), left column on the left
    topLeft = scene.cellCenterOnScreen((0, 0), width, height)
    bottomRight = scene.cellCenterOnScreen((2, 2), width, height)
    assert topLeft[0] < bottomRight[0]
    assert topLeft[1] < bottomRight[1]


def test_a_press_off_the_board_picks_no_cell():
    assert scene.pickCell((5, 5), 800, 600) is None
    assert scene.pickCell((795, 595), 800, 600) is None
    assert scene.pickCell(None, 800, 600) is None


def test_a_panel_button_keeps_the_2d_buttons_centre_and_at_least_its_size():
    quit = button()
    x, y, w, h = scene.buttonRect(quit, 800, 600)
    assert x + w / 2 == pytest.approx(400)
    assert w >= 100 and h == 50 and y == 500


def test_a_long_label_widens_its_button_to_fit():
    playAgain = button("Play Again", ypos=400)
    x, y, w, h = scene.buttonRect(playAgain, 800, 600)
    assert w >= len("Play Again") * scene.buttonPixelSize(playAgain, 800, 600)


def test_a_button_is_hit_inside_and_missed_outside_with_the_2d_edges():
    quit = button()
    x, y, w, h = scene.buttonRect(quit, 800, 600)
    assert scene.buttonHit(quit, (x, y), 800, 600)
    assert scene.buttonHit(quit, (x + w / 2, y + h / 2), 800, 600)
    assert not scene.buttonHit(quit, (x + w, y), 800, 600)
    assert not scene.buttonHit(quit, (x, y + h), 800, 600)
    assert not scene.buttonHit(quit, None, 800, 600)


def test_buttons_follow_the_window_when_it_is_resized():
    quit = button()
    x, y, w, h = scene.buttonRect(quit, 1600, 1200)
    assert (x + w / 2, y) == pytest.approx((800, 1000))


def test_a_cell_button_is_hit_through_its_tile():
    cellButton = button("", cell=(1, 1))
    centre = scene.cellCenterOnScreen((1, 1), 800, 600)
    other = scene.cellCenterOnScreen((0, 0), 800, 600)
    assert scene.buttonHit(cellButton, centre, 800, 600)
    assert not scene.buttonHit(cellButton, other, 800, 600)


@pytest.mark.parametrize("color", [(0, 0, 0), (255, 255, 255), (120, 40, 200), (250, 250, 10)])
def test_hover_lifts_a_colour_as_graphik_does_in_2d(color):
    assert scene.hoverColor(color) == Graphik._hoverColor(color)


def test_marks_stand_on_their_cells():
    cells = emptyCells()
    cells[(0, 0)] = "X"
    cells[(2, 1)] = "O"
    pieces = scene.boardPieces(cells)
    assert {(p.column, p.row, p.style) for p in pieces} == {(0, 0, "X"), (2, 1, "O")}


def test_an_x_and_an_o_add_their_own_shapes_to_the_board():
    empty = scene.buildScene(emptyCells(), [], [], 800, 600)
    cells = emptyCells()
    cells[(1, 1)] = "X"
    withX = scene.buildScene(cells, [], [], 800, 600)
    cells[(0, 0)] = "O"
    withBoth = scene.buildScene(cells, [], [], 800, 600)
    assert len(withX.shapes) > len(empty.shapes)
    assert len(withBoth.shapes) > len(withX.shapes)
    discs = [s for s in withBoth.shapes if s.kind == CYLINDER]
    assert len(discs) == 2


def test_the_board_screen_has_no_overlay_and_a_text_screen_dims_the_board():
    cellButtons = [button("", cell=cell) for _, cell, _ in scene.CELLS]
    board = scene.buildScene(emptyCells(), [], cellButtons, 800, 600)
    title = scene.buildScene(emptyCells(), [("Tic Tac Toe", 400, 150, 64, (0, 0, 0))],
                             [button("Start", ypos=300)], 800, 600)
    assert board.panels == [] and board.labels == []
    assert title.panels[0].width == 800 and title.panels[0].height == 600
    assert [label.text for label in title.labels] == ["Tic Tac Toe", "Start"]


def test_a_headline_is_centred_where_the_2d_text_is():
    label = scene.headlineLabel("You won!", 400, 150, 64, 800, 600)
    assert label.x + len("You won!") * label.pixelSize / 2 == pytest.approx(400)
    assert label.y + label.pixelSize / 2 == pytest.approx(150)
    assert label.x >= 0 and label.x + len("You won!") * label.pixelSize <= 800


def test_hovering_a_cell_lights_its_tile_and_hovering_a_button_lifts_it():
    cellButtons = [button("", cell=cell) for _, cell, _ in scene.CELLS]
    plain = scene.buildScene(emptyCells(), [], cellButtons, 800, 600)
    centre = scene.cellCenterOnScreen((2, 0), 800, 600)
    hovered = scene.buildScene(emptyCells(), [], cellButtons, 800, 600, pointer=centre)
    assert len(hovered.shapes) == len(plain.shapes) + 1
    slab = hovered.shapes[-1]
    assert slab.position[0] == pytest.approx(1.0) and slab.position[2] == pytest.approx(-1.0)

    quit = button()
    x, y, w, h = scene.buttonRect(quit, 800, 600)
    still = scene.buildScene(emptyCells(), [], [quit], 800, 600)
    lifted = scene.buildScene(emptyCells(), [], [quit], 800, 600, pointer=(x + 1, y + 1))
    assert lifted.panels[1].color != still.panels[1].color


def test_the_recorder_keeps_text_and_buttons_and_clears_per_frame():
    recorder = scene.ScreenRecorder()
    recorder.drawText("Tic Tac Toe", 400, 150, 64, (0, 0, 0))
    recorder.drawRectangle(0, 0, 10, 10, (0, 0, 0))
    recorder.drawButton(1, 2, 3, 4, (0, 0, 0), (255, 255, 255), 20, "Start", None)
    assert recorder.texts == [("Tic Tac Toe", 400, 150, 64, (0, 0, 0))]
    assert recorder.buttons == [(1, 2, 3, 4, (0, 0, 0), (255, 255, 255), 20, "Start")]
    recorder.clear()
    assert recorder.texts == [] and recorder.buttons == []


# -- a phone held upright (graphik 0.5.2 frames the board for the window's shape)


def boardBox(width, height):
    from preponderous.graphik.grid3d import projectToScreen

    camera = scene.camera(width, height)
    half = scene.COLUMNS / 2.0 + scene.THEME.frameWidth
    points = [
        projectToScreen(camera, (x, y, z), width, height)
        for x in (-half, half)
        for z in (-half, half)
        for y in (-scene.THEME.tileHeight, 0.3)
    ]
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


@pytest.mark.parametrize("size", [(390, 844), (844, 390), (1280, 800), (800, 600)])
def test_the_whole_board_is_on_screen_at_any_shape(size):
    left, top, right, bottom = boardBox(*size)
    assert left >= 0 and top >= 0 and right <= size[0] and bottom <= size[1]


def test_on_a_phone_held_upright_the_board_fills_the_width():
    left, top, right, bottom = boardBox(390, 844)
    assert right - left >= 0.85 * 390
    # and a tap on a cell's middle picks that cell
    for cell in [(0, 0), (1, 1), (2, 2)]:
        assert scene.pickCell(scene.cellCenterOnScreen(cell, 390, 844), 390, 844) == cell


def test_text_drawn_where_earlier_text_was_replaces_it():
    # as the 2D window paints over it: the board's status line is redrawn mid-frame on a move
    recorder = scene.ScreenRecorder()
    recorder.drawText("Your turn: you are X", 400, 60, 32, (0, 0, 0))
    recorder.drawText("Tic Tac Toe", 400, 150, 64, (0, 0, 0))
    recorder.drawText("The computer (O) is thinking...", 400, 60, 32, (0, 0, 0))
    assert [text for text, *_ in recorder.texts] == ["Tic Tac Toe", "The computer (O) is thinking..."]


def test_a_headline_on_a_phone_is_no_smaller_than_a_button_label():
    # the 2D layout shrinks to about half on a phone held upright, which left the board's
    # status line at about 11 pixels
    label = scene.headlineLabel("Your turn: you are X", 400, 60, 32, 390, 844)
    assert label.pixelSize >= scene.MIN_BUTTON_TEXT
    assert label.x >= 0 and label.x + len(label.text) * label.pixelSize <= 390


def test_the_winning_line_is_lit_under_its_marks():
    # the end screens keep the board, and the line of three is what says how it was won or lost
    cells = emptyCells()
    for cell in [(2, 0), (1, 1), (0, 2)]:
        cells[cell] = "O"
    cells[(0, 0)] = "X"
    assert scene.winningCells(cells) == [(2, 0), (1, 1), (0, 2)]
    lit = scene.buildScene(cells, [("You lost!", 400, 150, 64, (0, 0, 0))], [], 800, 600)
    unlit = scene.buildScene(emptyCells(), [], [], 800, 600)
    gold = [shape for shape in lit.shapes if tuple(shape.color[:3]) == scene.WIN_COLOR]
    assert len(gold) == 3
    assert not [shape for shape in unlit.shapes if tuple(shape.color[:3]) == scene.WIN_COLOR]
    assert scene.winningCells(emptyCells()) == []


def lostCells():
    cells = emptyCells()
    for cell in [(2, 0), (1, 1), (0, 2), (1, 2)]:
        cells[cell] = "O"
    for cell in [(0, 0), (1, 0), (0, 1), (2, 1)]:
        cells[cell] = "X"
    return cells


@pytest.mark.parametrize("size", [(390, 844), (1280, 800)])
def test_an_end_screens_headline_and_play_again_keep_off_the_played_board(size):
    # the marks and the lit line say how it ended, so nothing covers them where there is room
    width, height = size
    playAgain = button("Play Again", 350, 400, 100, 50)  # where the end screens draw it in 2D
    headline = ("You lost!", 400, 150, 64, (0, 0, 0))
    board = scene.boardScreenBox(width, height)
    assert scene.endScreenBoard(lostCells(), [playAgain], width, height) == board
    built = scene.buildScene(lostCells(), [headline], [playAgain], width, height)
    panel = [p for p in built.panels if p.width < width][0]
    assert not scene._overlaps(panel.x, panel.y, panel.width, panel.height, board)
    label = [lab for lab in built.labels if lab.text == "You lost!"][0]
    assert not scene._overlaps(label.x, label.y, scene.measureText(label.text, label.pixelSize),
                               label.pixelSize, board)
    assert label.y >= 0 and panel.y + panel.height <= height
    # and a press lands where the button is drawn
    shift = scene.endScreenShift(lostCells(), [playAgain], width, height)
    assert shift > 0
    centre = (panel.x + panel.width / 2, panel.y + panel.height / 2)
    assert scene.buttonHit(playAgain, centre, width, height, shift=shift)
    assert not scene.buttonHit(playAgain, centre, width, height)  # where 2D's layout would put it


def test_an_end_screens_buttons_move_together_or_not_at_all():
    # the desktop window's end screens have Play Again and Quit, one above the other
    playAgain, quit = button("Play Again", 350, 400, 100, 50), button("Quit", 350, 500, 100, 50)
    for width, height in [(800, 600), (390, 844), (1280, 800)]:
        shift = scene.endScreenShift(lostCells(), [playAgain, quit], width, height)
        a = scene.buttonRect(playAgain, width, height, shift=shift)
        b = scene.buttonRect(quit, width, height, shift=shift)
        assert a[1] + a[3] <= b[1]  # still in order, never on top of each other
        assert b[1] + b[3] <= height


def test_the_title_and_board_screens_keep_their_layout():
    start = button("Start", 350, 300, 100, 50)
    assert scene.endScreenBoard(emptyCells(), [start], 390, 844) is None  # the title: no marks
    cellButton = button("", 0, 0, 10, 10, cell=(0, 0))
    assert scene.endScreenBoard(lostCells(), [cellButton], 390, 844) is None  # playing
