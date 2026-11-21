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
