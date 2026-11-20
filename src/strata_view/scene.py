"""What the 3D window shows, as plain data (no Strata, no GPU).

The 3D view runs the 2D game's own screens: each frame they draw their text
and buttons as usual, and a ScreenRecorder (standing in for Graphik) keeps
them. buildScene() turns that frame into a Scene for graphik's 3D grid view:

- the board is a 3x3 grid of tiles, with an X or an O standing on every
  claimed cell (the game's own cell attributes);
- the grid screen's nine cell buttons are the tiles themselves, picked by
  projecting each tile onto the window (pickCell);
- every other button (Start, Play Again, Quit) is a screen panel, and every
  headline ("Tic Tac Toe", "You won!") is screen text, laid out from the 2D
  window's 800x600 coordinates scaled to the 3D window.

So every screen, button and handler is the 2D game's, and only how they look
and how a press finds them differ.
"""

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from preponderous.graphik.grid3d import (
    BED_TOP,
    CUBE,
    CYLINDER,
    SPHERE,
    TEXT_COLOR,
    GridBoard,
    Label,
    Panel,
    Piece,
    PieceStyle,
    Shape,
    Theme,
    rgb255,
    rgba,
    shade,
)

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


def projectToScreen(cam, point, width, height):
    """Where a world point lands in the window, in pixels from the top-left,
    or None when it's behind the camera. The same right-handed look-at and
    OpenGL perspective grid3d asks Strata for (up is +y); Strata 0.7.0 has no
    projection call of its own, so it's done here."""

    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    def cross(a, b):
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )

    def unit(a):
        length = math.sqrt(dot(a, a))
        return (a[0] / length, a[1] / length, a[2] / length)

    forward = unit(sub(cam.target, cam.eye))
    right = unit(cross(forward, (0.0, 1.0, 0.0)))
    up = cross(right, forward)
    offset = sub(point, cam.eye)
    depth = dot(offset, forward)
    if depth <= 0:
        return None
    focal = 1.0 / math.tan(math.radians(cam.fovDegrees) / 2.0)
    aspect = width / float(height)
    ndcX = focal / aspect * dot(offset, right) / depth
    ndcY = focal * dot(offset, up) / depth
    return ((ndcX + 1.0) / 2.0 * width, (1.0 - ndcY) / 2.0 * height)


def cellOutline(cell, width, height):
    """The four window corners of a cell's tile top (the whole cell, gaps
    shared with its neighbours, so no press between tiles is lost)."""
    cam = camera(width, height)
    x, z = BOARD.cellCenter(*cell)
    corners = [(x - 0.5, z - 0.5), (x + 0.5, z - 0.5), (x + 0.5, z + 0.5), (x - 0.5, z + 0.5)]
    return [projectToScreen(cam, (cx, BED_TOP, cz), width, height) for cx, cz in corners]


def cellCenterOnScreen(cell, width, height):
    x, z = BOARD.cellCenter(*cell)
    return projectToScreen(camera(width, height), (x, BED_TOP, z), width, height)


def _insideConvex(point, polygon):
    sign = 0
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:] + polygon[:1]):
        cross = (bx - ax) * (point[1] - ay) - (by - ay) * (point[0] - ax)
        if cross != 0:
            if sign == 0:
                sign = 1 if cross > 0 else -1
            elif (cross > 0) != (sign > 0):
                return False
    return True


def pickCell(pos, width, height):
    """The (column, row) of the tile under a window position, or None."""
    if pos is None:
        return None
    for _, cell, _ in CELLS:
        outline = cellOutline(cell, width, height)
        if None not in outline and _insideConvex(pos, outline):
            return cell
    return None


def layoutScale(width, height):
    """How the 2D window's coordinates stretch to this window: (sx, sy, s),
    where s scales sizes (text) without distorting them."""
    sx, sy = width / float(LAYOUT_WIDTH), height / float(LAYOUT_HEIGHT)
    return sx, sy, min(sx, sy)


def buttonPixelSize(button, width, height):
    return button.sizeText * BUTTON_TEXT_SCALE * layoutScale(width, height)[2]


def buttonRect(button, width, height):
    """A non-cell button's rectangle in the window: the 2D box scaled to the
    window, widened about its centre when Strata's wider font needs it."""
    sx, sy, _ = layoutScale(width, height)
    w, h = button.width * sx, button.height * sy
    textWidth = len(button.text) * buttonPixelSize(button, width, height) + 2 * BUTTON_PADDING
    centerX = (button.xpos + button.width / 2.0) * sx
    w = max(w, textWidth)
    return (centerX - w / 2.0, button.ypos * sy, w, h)


def buttonHit(button, pos, width, height):
    """True when a press at window position `pos` lands on the button: a
    cell's tile as it appears in 3D, or a panel's rectangle."""
    if pos is None:
        return False
    if button.cell is not None:
        return pickCell(pos, width, height) == button.cell
    x, y, w, h = buttonRect(button, width, height)
    # the same edges graphik's 2D check uses: left and top in, right and bottom out
    return x <= pos[0] < x + w and y <= pos[1] < y + h


def hoverColor(color):
    """graphik's hover lift (Graphik._hoverColor): light colours darken by
    25, the rest lighten by 35, on the 0-255 scale."""
    shift = -25 if sum(color[:3]) / 3.0 >= 128 else 35
    return tuple(max(0, min(255, c + shift)) for c in color[:3])


def _centredLabel(text, centerX, centerY, pixelSize, color):
    return Label(text, centerX - len(text) * pixelSize / 2.0, centerY - pixelSize / 2.0,
                 pixelSize, color)


def headlineLabel(text, xpos, ypos, size, width, height):
    """graphik's drawText centres its text on (xpos, ypos)."""
    sx, sy, s = layoutScale(width, height)
    pixelSize = size * TEXT_SCALE * s
    # never wider than the window
    pixelSize = min(pixelSize, (width - 2 * BUTTON_PADDING) / max(1, len(text)))
    # the 2D window paints black text on white; the 3D background is dark
    return _centredLabel(text, xpos * sx, ypos * sy, pixelSize, TEXT_COLOR)


def buttonPanelAndLabel(button, width, height, hovered):
    x, y, w, h = buttonRect(button, width, height)
    box = hoverColor(button.colorBox) if hovered else button.colorBox
    panel = Panel(x, y, w, h, rgba(rgb255(box), 0.92))
    label = _centredLabel(button.text, x + w / 2.0, y + h / 2.0,
                          buttonPixelSize(button, width, height),
                          rgba(rgb255(button.colorText)))
    return panel, label


def hoverShapes(cell):
    """A thin glowing slab on the tile under the pointer (the 2D window lifts
    a hovered grid slot's colour)."""
    x, z = BOARD.cellCenter(*cell)
    edge = 1.0 - THEME.tileGap
    return [Shape(CUBE, (x, BED_TOP + 0.005, z), (edge, 0.01, edge), rgba(HOVER_COLOR))]


def buildScene(cells, texts, buttons, width, height, pointer=None):
    """The Scene for one frame.

    cells: (column, row) -> "X"/"O"/"" (boardCells); texts: the screen's
    drawText calls; buttons: Button objects; pointer: the mouse position in
    the window, for hover feedback, or None.
    """
    hasCells = any(button.cell is not None for button in buttons)
    labels, panels = [], []
    if not hasCells:
        # a screen of text and buttons over the board, as the 2D screens are
        # drawn over a blank window
        panels.append(Panel(0, 0, width, height, OVERLAY_COLOR))
    for text, xpos, ypos, size, color in texts:
        labels.append(headlineLabel(text, xpos, ypos, size, width, height))
    hoveredCell = None
    for button in buttons:
        hovered = buttonHit(button, pointer, width, height)
        if button.cell is not None:
            if hovered:
                hoveredCell = button.cell
            continue
        panel, label = buttonPanelAndLabel(button, width, height, hovered)
        panels.append(panel)
        labels.append(label)
    scene = BOARD.scene(
        boardPieces(cells), labels=labels, panels=panels, aspect=width / float(height)
    )
    if hoveredCell is not None:
        scene.shapes.extend(hoverShapes(hoveredCell))
    return scene
