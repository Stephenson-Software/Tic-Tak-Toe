# Entry point for the browser build: pygbag (https://pygame-web.github.io) packages this
# folder and runs main.py. The desktop entry point stays src/tictactoe.py.
import asyncio

# pygbag decides which packages to load into the browser from main.py's own imports, so
# pygame must be imported here even though only tictactoe.py uses it directly.
import pygame  # noqa: F401

from tictactoe import TicTacToe

asyncio.run(TicTacToe().titleScreen())
