import inspect

import pygame
import pytest

import Graphik as graphikModule
from Graphik import Graphik


#  A 100x50 button at (200, 300), the size every end-screen button uses.
BUTTON = (200, 300, 100, 50)


class FakeDisplay:
    pass


#  Keeps what drawText blits so its placement can be asserted without a window.
class RecordingDisplay:
    def __init__(self):
        self.blits = []

    def blit(self, surface, rectangle):
        self.blits.append((surface, rectangle))


def pressButton(graphik, monkeypatch, mousePosition, pressedButtons):
    #  Drawing is suppressed so only drawButton's click check is exercised; the mouse is
    #  replaced with a fixed position and button state for the single frame drawn.
    monkeypatch.setattr(graphik, "drawRectangle", lambda *args: None)
    monkeypatch.setattr(graphik, "drawText", lambda *args: None)
    monkeypatch.setattr(graphikModule.pygame.mouse, "get_pos", lambda: mousePosition)
    monkeypatch.setattr(graphikModule.pygame.mouse, "get_pressed", lambda: pressedButtons)

    clicks = []
    xpos, ypos, width, height = BUTTON
    graphik.drawButton(xpos, ypos, width, height, (0, 0, 0), (255, 255, 255), 20, "Quit", lambda: clicks.append(1))
    return len(clicks)


def test_game_display_is_returned_as_given():
    fakeDisplay = FakeDisplay()

    assert Graphik(fakeDisplay).getGameDisplay() is fakeDisplay


def test_constructor_requires_a_game_display():
    #  Graphik never opens a display of its own: the only constructor takes the display the
    #  game already created, so calling it without one is an error rather than a 900x600 window.
    with pytest.raises(TypeError):
        Graphik()


def test_constructor_has_exactly_one_definition():
    #  Issue #12: a second __init__ used to silently shadow the first. The source is checked
    #  directly because Python keeps only the last definition, which hides the duplicate.
    source = inspect.getsource(Graphik)

    assert source.count("def __init__(") == 1


def test_constructor_assigns_only_the_game_display_and_an_empty_font_cache():
    #  The color attributes of the removed, shadowed __init__ were never present on an
    #  instance, so nothing is expected here beyond the display that was passed in and the
    #  cache that getFont fills. No font is opened until one is needed.
    graphik = Graphik(FakeDisplay())

    assert vars(graphik) == {"gameDisplay": graphik.gameDisplay, "fonts": {}}


def test_get_version_is_not_offered():
    #  Issue #12: getVersion returned self.version, which no code ever assigned, so every call
    #  raised AttributeError. The method has been removed rather than left as a guaranteed error.
    assert not hasattr(Graphik, "getVersion")


def test_rectangle_fills_exactly_the_given_area():
    surface = pygame.Surface((50, 50))
    surface.fill((255, 255, 255))

    Graphik(surface).drawRectangle(10, 20, 5, 4, (0, 0, 0))

    assert surface.get_at((10, 20))[:3] == (0, 0, 0)
    assert surface.get_at((14, 23))[:3] == (0, 0, 0)
    assert surface.get_at((15, 23))[:3] == (255, 255, 255)
    assert surface.get_at((14, 24))[:3] == (255, 255, 255)


def test_text_is_centered_on_the_given_position():
    pygame.font.init()
    display = RecordingDisplay()

    Graphik(display).drawText("Play Again", 250, 325, 16, (255, 255, 255))

    assert len(display.blits) == 1
    assert display.blits[0][1].center == (250, 325)


def recordFontOpens(monkeypatch):
    realFont = pygame.font.Font
    opens = []

    def openFont(name, size):
        opens.append((name, size))
        return realFont(name, size)

    monkeypatch.setattr(graphikModule.pygame.font, "Font", openFont)
    return opens


def test_each_text_size_opens_its_font_only_once(monkeypatch):
    #  Every frame redraws every text, so opening a font per text would repeat on each frame.
    pygame.font.init()
    opens = recordFontOpens(monkeypatch)
    graphik = Graphik(RecordingDisplay())

    for _ in range(3):
        graphik.drawText("Start", 400, 300, 20, (0, 0, 0))
        graphik.drawText("Quit", 400, 500, 20, (0, 0, 0))
        graphik.drawText("Play Again", 400, 400, 16, (0, 0, 0))

    assert opens == [("freesansbold.ttf", 20), ("freesansbold.ttf", 16)]


def test_text_is_rendered_at_the_size_it_asks_for_after_another_size_was_drawn():
    #  The cache is keyed by size: a shared font would draw the second text at the first size.
    pygame.font.init()
    display = RecordingDisplay()
    graphik = Graphik(display)

    graphik.drawText("X", 0, 0, 64, (0, 0, 0))
    graphik.drawText("X", 0, 0, 16, (0, 0, 0))

    assert display.blits[1][0].get_size() == pygame.font.Font("freesansbold.ttf", 16).size("X")


def test_a_new_graphik_opens_its_own_fonts(monkeypatch):
    #  A font outlives neither pygame.quit nor pygame.font.quit, so the cache belongs to the
    #  instance rather than to the module: a later Graphik must not inherit a dead font.
    pygame.font.init()
    opens = recordFontOpens(monkeypatch)

    Graphik(RecordingDisplay()).drawText("Start", 400, 300, 20, (0, 0, 0))
    Graphik(RecordingDisplay()).drawText("Start", 400, 300, 20, (0, 0, 0))

    assert len(opens) == 2


def test_button_draws_its_box_then_its_label_centered_inside_it(monkeypatch):
    graphik = Graphik(FakeDisplay())
    calls = []
    monkeypatch.setattr(graphik, "drawRectangle", lambda *args: calls.append(("drawRectangle",) + args))
    monkeypatch.setattr(graphik, "drawText", lambda *args: calls.append(("drawText",) + args))
    monkeypatch.setattr(graphikModule.pygame.mouse, "get_pos", lambda: (0, 0))
    monkeypatch.setattr(graphikModule.pygame.mouse, "get_pressed", lambda: (0, 0, 0))

    graphik.drawButton(200, 300, 100, 50, (0, 0, 0), (255, 255, 255), 20, "Quit", lambda: None)

    assert calls == [
        ("drawRectangle", 200, 300, 100, 50, (0, 0, 0)),
        ("drawText", "Quit", 250, 325, 20, (255, 255, 255)),
    ]


def test_left_click_inside_the_button_calls_its_function(monkeypatch):
    assert pressButton(Graphik(FakeDisplay()), monkeypatch, (250, 325), (1, 0, 0)) == 1


def test_hovering_without_a_click_does_not_call_the_function(monkeypatch):
    assert pressButton(Graphik(FakeDisplay()), monkeypatch, (250, 325), (0, 0, 0)) == 0


@pytest.mark.parametrize("pressedButtons", [(0, 1, 0), (0, 0, 1)], ids=["middle", "right"])
def test_only_the_left_mouse_button_clicks(monkeypatch, pressedButtons):
    assert pressButton(Graphik(FakeDisplay()), monkeypatch, (250, 325), pressedButtons) == 0


def test_left_click_still_counts_while_another_button_is_held(monkeypatch):
    assert pressButton(Graphik(FakeDisplay()), monkeypatch, (250, 325), (1, 0, 1)) == 1


#  The hit-box uses strict comparisons, so a click on the button's outline is ignored and
#  only the pixels strictly inside it register. The right and bottom edges sit at
#  xpos + width and ypos + height, one pixel past the last pixel drawRectangle fills.
@pytest.mark.parametrize("mousePosition, clicks", [
    ((200, 325), 0),
    ((201, 325), 1),
    ((299, 325), 1),
    ((300, 325), 0),
    ((250, 300), 0),
    ((250, 301), 1),
    ((250, 349), 1),
    ((250, 350), 0),
], ids=["left edge", "just inside left", "just inside right", "right edge",
        "top edge", "just inside top", "just inside bottom", "bottom edge"])
def test_click_registers_only_strictly_inside_the_button(monkeypatch, mousePosition, clicks):
    assert pressButton(Graphik(FakeDisplay()), monkeypatch, mousePosition, (1, 0, 0)) == clicks


def test_holding_the_click_calls_the_function_on_every_frame_drawn(monkeypatch):
    #  drawButton checks the mouse each time it is drawn, not on a button-down event, so a
    #  click held across three frames calls the function three times.
    graphik = Graphik(FakeDisplay())

    clicks = sum(pressButton(graphik, monkeypatch, (250, 325), (1, 0, 0)) for _ in range(3))

    assert clicks == 3
