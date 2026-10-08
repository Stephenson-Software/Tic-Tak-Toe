import ast
import os
import runpy

import tictactoe


#  The browser entry point pygbag packages and runs.
MAIN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "main.py")


def runMain(monkeypatch):
    #  The title screen loops forever in production, so it is replaced with a coroutine that
    #  records which game it was awaited on. main.py imports TicTacToe from the tictactoe module
    #  these tests already imported, so replacing the method on the class reaches it.
    monkeypatch.setattr(tictactoe.sys, "platform", "linux")
    started = []

    async def recordTitleScreen(self):
        started.append(self)

    monkeypatch.setattr(tictactoe.TicTacToe, "titleScreen", recordTitleScreen)
    runpy.run_path(MAIN_PATH, run_name="__main__")
    return started


def test_main_awaits_the_title_screen_of_a_new_game(monkeypatch):
    started = runMain(monkeypatch)

    assert len(started) == 1
    assert isinstance(started[0], tictactoe.TicTacToe)


def test_main_imports_pygame_itself():
    #  pygbag decides which packages to load into the browser from main.py's own imports.
    with open(MAIN_PATH) as mainFile:
        tree = ast.parse(mainFile.read())

    imported = [alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names]

    assert "pygame" in imported
