"""Tic Tac Toe's 3D view, drawn with Strata (desktop Linux and Windows).

scene.py maps the game's state and the screen's buttons and text to plain
shapes and needs no GPU; game.py runs the same screens, buttons and rules as
the 2D window in a Strata window, through graphik's 3D grid view
(preponderous.graphik.grid3d). On Linux and Windows `python3 src/tictactoe.py`
opens it by default and falls back to the 2D window when Strata can't start
(`--2d` skips it). tools/strata_snapshot.py renders real game states headless
to PNGs.
"""


class StrataUnavailable(Exception):
    """The 3D window can't start here: graphik's 3D grid view or the
    strata-engine package is missing, the Strata library couldn't be loaded,
    or no window could be opened. The message says which, in words a player
    can act on."""


def runStrataGame():
    """Plays the game in a Strata window; raises StrataUnavailable, before any
    window opens, when the 3D view can't run here."""
    try:
        from preponderous.graphik import grid3d  # noqa: F401
    except ImportError:
        raise StrataUnavailable(
            "the installed graphik has no 3D grid view (preponderous.graphik.grid3d)"
        )
    from strata_view.game import runStrataGame as run

    run()
