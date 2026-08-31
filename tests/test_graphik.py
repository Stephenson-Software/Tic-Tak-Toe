import pytest

from Graphik import Graphik


class FakeDisplay:
    pass


def test_game_display_is_returned_as_given():
    fakeDisplay = FakeDisplay()

    assert Graphik(fakeDisplay).getGameDisplay() is fakeDisplay


def test_constructor_requires_a_game_display():
    #  Characterizes the second __init__ shadowing the first (issue #12): the no-argument
    #  constructor documented by the dead first definition cannot be called.
    with pytest.raises(TypeError):
        Graphik()


def test_color_attributes_are_not_assigned():
    #  Also issue #12 — black/white/red/green/blue are only set by the shadowed __init__.
    graphik = Graphik(FakeDisplay())

    for colorName in ["black", "white", "red", "green", "blue"]:
        assert not hasattr(graphik, colorName)


def test_get_version_raises_because_version_is_never_assigned():
    #  Also issue #12 — self.version has no assignment anywhere in the module.
    with pytest.raises(AttributeError):
        Graphik(FakeDisplay()).getVersion()
