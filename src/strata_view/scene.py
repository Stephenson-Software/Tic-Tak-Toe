"""What the 3D window shows, as plain data (no Strata, no GPU).

The 3D view runs the 2D game's own screens: each frame they draw their text
and buttons as usual, and a ScreenRecorder (standing in for Graphik) keeps
them. buildScene() turns that frame into a Scene for graphik's 3D grid view:

- the board is a 3x3 grid of tiles, with an X or an O standing on every
  claimed cell (the game's own cell attributes);
- the grid screen's nine cell buttons are the tiles themselves, picked
  through graphik grid3d's pickCell (the ray through the pointer meets the
  board), and the tile under the pointer gets grid3d's hover slab;
- every other button (Start, Play Again, Quit) is a screen panel, and every
  headline ("Tic Tac Toe", "You won!") is screen text, laid out from the 2D
  window's 800x600 coordinates scaled to the 3D window; buttons are
  grid3d's screen Buttons (graphik's 2D edges and hover lift).

So every screen, button and handler is the 2D game's, and only how they look
and how a press finds them differ.
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple

# BED_TOP, hoverColor and projectToScreen are re-exported for the tools and tests.
from preponderous.graphik.grid3d import (
    BED_TOP,
    CUBE,
    CYLINDER,
    SPHERE,
    TEXT_COLOR,
    GridBoard,
    Panel,
    Piece,
    PieceStyle,
    Shape,
    Theme,
    cellScreenPosition,
    centredLabel,
    hoverColor,
    measureText,
    pickCell as _pickCell,
    projectToScreen,
    rgba,
    shade,
)
from preponderous.graphik.grid3d import Button as ScreenButton

# The 2D window's size: the screens lay out their text and buttons in it.
LAYOUT_WIDTH = 800
LAYOUT_HEIGHT = 600

COLUMNS = ROWS = 3

# Each cell's handler on TicTacToe (the function its grid slot button runs),
# with the cell's (column, row) and the attribute holding its mark. Row 0 is
# the top row of the 2D board and the far edge of the 3D one.
CELLS = [
    ("topLeft", (0, 0), "topLeftL"),
    ("topMiddle", (1, 0), "topMiddleL"),
    ("topRight", (2, 0), "topRightL"),
    ("middleLeft", (0, 1), "middleLeftL"),
    ("middleMiddle", (1, 1), "middleMiddleL"),
    ("middleRight", (2, 1), "middleRightL"),
    ("bottomLeft", (0, 2), "bottomLeftL"),
    ("bottomMiddle", (1, 2), "bottomMiddleL"),
    ("bottomRight", (2, 2), "bottomRightL"),
]
CELL_OF_HANDLER = {handler: cell for handler, cell, _ in CELLS}

X_COLOR = (0.86, 0.22, 0.18)
O_COLOR = (0.20, 0.46, 0.88)
HOVER_COLOR = (1.0, 0.86, 0.35)
TILE_LIGHT = (0.86, 0.85, 0.80)
TILE_DARK = (0.78, 0.77, 0.72)
FRAME_COLOR = (0.10, 0.10, 0.12)
# Dims the board behind a screen that has no cells to press (title, end screens)
OVERLAY_COLOR = (0.04, 0.05, 0.07, 0.55)
# The 2D font (freesansbold) is narrower than Strata's monospaced one, which
# is about one pixel size wide per character, so text is set a little smaller
TEXT_SCALE = 0.72
BUTTON_TEXT_SCALE = 0.9
BUTTON_PADDING = 14
# Never smaller than this, in pixels: on a phone held upright the 2D layout
# shrinks to about half, which would leave a button's label too small to read
# (the panel widens to fit it, so the button stays an easy tap)
MIN_BUTTON_TEXT = 14

MARK_HEIGHT = 0.16
MARK_BASE_HEIGHT = 0.04


def _xMark(piece, x, z, baseY):
    """An X from small cubes laid along both diagonals (Strata 0.7.0 can't
    rotate a shape, so each stroke is a staircase of overlapping cubes)."""
    shapes = []
    steps = 9
    reach = 0.27
    block = 0.13
    y = baseY + MARK_BASE_HEIGHT + MARK_HEIGHT / 2
    for i in range(steps):
        t = -reach + 2 * reach * i / (steps - 1)
        for dz in (t, -t):
            if i == steps // 2 and dz == -t:
                continue  # the centre block is shared by both strokes
            shapes.append(
                Shape(CUBE, (x + t, y, z + dz), (block, MARK_HEIGHT, block), rgba(X_COLOR))
            )
    return shapes


def _oMark(piece, x, z, baseY):
    """An O as a ring of spheres."""
    shapes = []
    beads = 16
    radius = 0.26
    bead = 0.15
    y = baseY + MARK_BASE_HEIGHT + MARK_HEIGHT / 2
    for i in range(beads):
        angle = 2 * math.pi * i / beads
        shapes.append(
            Shape(
                SPHERE,
                (x + radius * math.cos(angle), y, z + radius * math.sin(angle)),
                (bead, MARK_HEIGHT, bead),
                rgba(O_COLOR),
            )
        )
    return shapes


THEME = Theme(
    tile=TILE_LIGHT,
    alternate=TILE_DARK,
    tileHeight=0.18,
    tileGap=0.12,
    frame=FRAME_COLOR,
    frameWidth=0.3,
    highlight=HOVER_COLOR,
    pieces={
        # a low disc under each mark, in the mark's colour, darkened
        "X": PieceStyle(kind=CYLINDER, color=shade(X_COLOR, 0.45), height=MARK_BASE_HEIGHT,
                        size=0.78, extras=_xMark),
        "O": PieceStyle(kind=CYLINDER, color=shade(O_COLOR, 0.45), height=MARK_BASE_HEIGHT,
                        size=0.78, extras=_oMark),
    },
)

BOARD = GridBoard(COLUMNS, ROWS, THEME)


@dataclass
class Button:
    """One button the screen drew this frame, in the 2D window's coordinates."""

    xpos: float
    ypos: float
    width: float
    height: float
    text: str
    colorBox: Tuple[int, int, int]
    colorText: Tuple[int, int, int]
    sizeText: int
    cell: Optional[Tuple[int, int]] = None  # (column, row) for a grid slot


class ScreenRecorder:
    """Stands in for Graphik in the 3D view: keeps what a screen draws in a
    frame (its text and buttons) instead of painting a pygame surface."""

    def __init__(self):
        self.clear()

    def clear(self):
        self.texts = []
        self.buttons = []

    def drawText(self, text, xpos, ypos, size, color):
        self.texts.append((text, xpos, ypos, size, color))

    def drawRectangle(self, xpos, ypos, width, height, color):
        # the black square behind the 2D grid; the 3D board has its own frame
        pass

    def drawButton(self, xpos, ypos, width, height, colorBox, colorText, sizeText, text, function):
        # function is the game's ignoreHeldButton: presses go through TicTacToe.pressButton
        self.buttons.append((xpos, ypos, width, height, colorBox, colorText, sizeText, text))


def frameButtons(buttons, recorded):
    """A frame's buttons as (Button, handler) pairs. TicTacToe.drawButton
    hands every button to its Graphik (here a ScreenRecorder, whose `buttons`
    are `recorded`) and to its own `buttons` (with the handler) in the same
    order, so the two lists line up."""
    paired = []
    for (xpos, ypos, width, height, text, function), drawn in zip(buttons, recorded):
        _, _, _, _, colorBox, colorText, sizeText, _ = drawn
        cell = CELL_OF_HANDLER.get(getattr(function, "__name__", None))
        paired.append((Button(xpos, ypos, width, height, text, colorBox, colorText, sizeText, cell), function))
    return paired


def boardCells(game):
    """(column, row) -> "X", "O" or "" for every cell, from the game's state."""
    return {cell: getattr(game, attribute) for _, cell, attribute in CELLS}


def boardPieces(cells):
    return [
        Piece(id=cell, column=cell[0], row=cell[1], style=mark)
        for cell, mark in sorted(cells.items())
        if mark in ("X", "O")
    ]


def camera(width, height):
    return BOARD.camera(width / float(height))


def cellCenterOnScreen(cell, width, height):
    return cellScreenPosition(camera(width, height), BOARD, cell[0], cell[1], width, height)


def pickCell(pos, width, height):
    """The (column, row) of the tile under a window position, or None. The
    whole cell counts, gaps shared with its neighbours, so no press between
    tiles is lost."""
    if pos is None:
        return None
    return _pickCell(camera(width, height), BOARD, pos[0], pos[1], width, height)


def layoutScale(width, height):
    """How the 2D window's coordinates stretch to this window: (sx, sy, s),
    where s scales sizes (text) without distorting them."""
    sx, sy = width / float(LAYOUT_WIDTH), height / float(LAYOUT_HEIGHT)
    return sx, sy, min(sx, sy)


def buttonPixelSize(button, width, height):
    return max(MIN_BUTTON_TEXT, button.sizeText * BUTTON_TEXT_SCALE * layoutScale(width, height)[2])


# How far below the page's 2D/3D button (in the browser) a headline or
# button that would run under it is moved
KEEP_CLEAR_GAP = 8


def _overlaps(x, y, w, h, area):
    ax, ay, aw, ah = area
    return x < ax + aw and x + w > ax and y < ay + ah and y + h > ay


def keepClearShift(x, y, w, h, keepClear):
    """How far down a box at (x, y, w, h) moves to stay out from under
    `keepClear` (x, y, width, height: the browser page's 2D/3D button), or
    0 when it is clear of it, or there is nothing to keep clear of."""
    if keepClear is None or not _overlaps(x, y, w, h, keepClear):
        return 0.0
    return keepClear[1] + keepClear[3] + KEEP_CLEAR_GAP - y


def screenButton(button, width, height, keepClear=None):
    """A non-cell button as a grid3d screen Button: the 2D box scaled to the
    window, widened about its centre when Strata's wider font needs it, and
    moved down out from under `keepClear` (the browser's 2D/3D button)."""
    sx, sy, _ = layoutScale(width, height)
    screen = ScreenButton(button.xpos * sx, button.ypos * sy, button.width * sx, button.height * sy,
                          button.text, button.colorBox, button.colorText,
                          buttonPixelSize(button, width, height), alpha=0.92,
                          padding=BUTTON_PADDING)
    screen.y += keepClearShift(*screen.rect(), keepClear)
    return screen


def buttonRect(button, width, height, keepClear=None):
    """A non-cell button's rectangle in the window (screenButton's)."""
    return screenButton(button, width, height, keepClear).rect()


def buttonHit(button, pos, width, height, keepClear=None):
    """True when a press at window position `pos` lands on the button: a
    cell's tile as it appears in 3D, or a panel's rectangle (with graphik's
    2D edges: left and top in, right and bottom out)."""
    if pos is None:
        return False
    if button.cell is not None:
        return pickCell(pos, width, height) == button.cell
    return screenButton(button, width, height, keepClear).contains(pos)


def headlineLabel(text, xpos, ypos, size, width, height, keepClear=None):
    """graphik's drawText centres its text on (xpos, ypos); the headline
    moves down out from under `keepClear` (the browser's 2D/3D button)."""
    sx, sy, s = layoutScale(width, height)
    pixelSize = size * TEXT_SCALE * s
    # never wider than the window
    pixelSize = min(pixelSize, (width - 2 * BUTTON_PADDING) / max(1, len(text)))
    # the 2D window paints black text on white; the 3D background is dark
    label = centredLabel(text, xpos * sx, ypos * sy, pixelSize, TEXT_COLOR)
    label.y += keepClearShift(label.x, label.y, measureText(text, pixelSize), pixelSize, keepClear)
    return label


def buttonPanelAndLabel(button, width, height, pointer, keepClear=None):
    """The panel (lifted while `pointer` is over it) and label of a non-cell button."""
    return screenButton(button, width, height, keepClear).draw(pointer)


def buildScene(cells, texts, buttons, width, height, pointer=None, keepClear=None):
    """The Scene for one frame.

    cells: (column, row) -> "X"/"O"/"" (boardCells); texts: the screen's
    drawText calls; buttons: Button objects; pointer: the mouse position in
    the window, for hover feedback, or None; keepClear: (x, y, width,
    height) that text and buttons stay out from under (the browser page's
    2D/3D button), or None.
    """
    hasCells = any(button.cell is not None for button in buttons)
    labels, panels = [], []
    if not hasCells:
        # a screen of text and buttons over the board, as the 2D screens are
        # drawn over a blank window
        panels.append(Panel(0, 0, width, height, OVERLAY_COLOR))
    for text, xpos, ypos, size, color in texts:
        labels.append(headlineLabel(text, xpos, ypos, size, width, height, keepClear))
    hoveredCell = None
    for button in buttons:
        hovered = buttonHit(button, pointer, width, height, keepClear)
        if button.cell is not None:
            if hovered:
                hoveredCell = button.cell
            continue
        panel, label = buttonPanelAndLabel(button, width, height, pointer, keepClear)
        panels.append(panel)
        labels.append(label)
    return BOARD.scene(
        boardPieces(cells), labels=labels, panels=panels, aspect=width / float(height),
        highlight=hoveredCell,
    )
