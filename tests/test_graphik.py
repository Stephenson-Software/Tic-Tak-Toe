import inspect

import pytest

from Graphik import Graphik


class FakeDisplay:
    pass


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


def test_constructor_assigns_only_the_game_display():
    #  The color attributes of the removed, shadowed __init__ were never present on an
    #  instance, so nothing is expected here beyond the display that was passed in.
    graphik = Graphik(FakeDisplay())

    assert list(vars(graphik)) == ["gameDisplay"]


def test_get_version_is_not_offered():
    #  Issue #12: getVersion returned self.version, which no code ever assigned, so every call
    #  raised AttributeError. The method has been removed rather than left as a guaranteed error.
    assert not hasattr(Graphik, "getVersion")
