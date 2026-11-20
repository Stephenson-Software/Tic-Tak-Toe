"""Which window `python3 src/tictactoe.py` opens, and the fallback to 2D."""

import sys

import pytest

import tictactoe


def args(*argv):
    return tictactoe.parseArguments(list(argv))


@pytest.mark.parametrize("platform", ["linux", "win32"])
def test_3d_is_the_default_where_strata_ships(platform):
    assert tictactoe.chooseInterface(args(), platform) == "3d"


def test_2d_is_the_default_elsewhere():
    assert tictactoe.chooseInterface(args(), "darwin") == "2d"


def test_the_2d_flag_skips_3d():
    assert tictactoe.chooseInterface(args("--2d"), "linux") == "2d"


def test_the_strata_flag_asks_for_3d_anywhere():
    assert tictactoe.chooseInterface(args("--strata"), "darwin") == "3d"


def test_the_two_flags_cannot_be_combined():
    with pytest.raises(SystemExit):
        args("--2d", "--strata")


def fakeStrataGame(monkeypatch, behaviour):
    import strata_view
    monkeypatch.setattr(strata_view, "runStrataGame", behaviour)
    return strata_view.StrataUnavailable


def fake2d(monkeypatch):
    started = []

    async def titleScreen(self):
        started.append(self)

    monkeypatch.setattr(tictactoe.TicTacToe, "titleScreen", titleScreen)
    monkeypatch.setattr(tictactoe.sys, "platform", "linux")
    return started


def test_when_3d_cannot_start_the_2d_game_starts_with_the_reason(monkeypatch, capsys):
    reasons = []

    def unavailable():
        raise reasons[0]

    StrataUnavailable = fakeStrataGame(monkeypatch, unavailable)
    reasons.append(StrataUnavailable("the strata-engine package isn't installed"))
    started = fake2d(monkeypatch)

    tictactoe.main([])

    out = capsys.readouterr().out
    assert "The 3D view isn't available here: the strata-engine package isn't installed." in out
    assert "--2d" in out
    assert len(started) == 1


def test_the_strata_flag_stops_with_the_reason_instead_of_falling_back(monkeypatch):
    reasons = []

    def unavailable():
        raise reasons[0]

    StrataUnavailable = fakeStrataGame(monkeypatch, unavailable)
    reasons.append(StrataUnavailable("no Strata window could be opened"))
    started = fake2d(monkeypatch)

    with pytest.raises(SystemExit) as stopped:
        tictactoe.main(["--strata"])

    assert "no Strata window could be opened" in str(stopped.value)
    assert started == []


def test_a_3d_game_that_runs_does_not_also_open_2d(monkeypatch):
    ran = []
    fakeStrataGame(monkeypatch, lambda: ran.append(True))
    started = fake2d(monkeypatch)

    tictactoe.main([])

    assert ran == [True] and started == []


def test_the_2d_flag_never_touches_strata(monkeypatch):
    def explode():
        raise AssertionError("3D was started")

    fakeStrataGame(monkeypatch, explode)
    started = fake2d(monkeypatch)

    tictactoe.main(["--2d"])

    assert len(started) == 1


def test_a_graphik_without_the_3d_grid_view_is_reported_before_any_window_opens(monkeypatch):
    import strata_view

    monkeypatch.setitem(sys.modules, "preponderous.graphik.grid3d", None)
    with pytest.raises(strata_view.StrataUnavailable, match="3D grid view"):
        strata_view.runStrataGame()
