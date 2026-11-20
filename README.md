# Tic-Tac-Toe

[![Play in your browser](https://img.shields.io/badge/Play-in%20your%20browser-2ea44f)](https://danielstephenson.dev/play/tic-tak-toe)

This game allows you to play Tic Tac Toe against the computer.

## Play in your browser
The game is also built for the browser with [pygbag](https://pygame-web.github.io) and served at https://tic-tak-toe.play.danielstephenson.dev, alongside the other games at https://danielstephenson.dev/play. Nothing needs to be installed: the page loads Python and pygame compiled to WebAssembly, then asks for a click or tap to start. The board and buttons work with a mouse or a tap on a phone. There is no Quit button in the browser build (closing the tab is how to leave).

To build and serve it locally:
```
python3 -m pip install pygbag==0.9.3
python3 -m pip install --no-deps --target src "$(grep -E '^graphik @ ' requirements.txt)"
python3 -m pygbag --build src
python3 -m http.server 8000 --bind 127.0.0.1 --directory src/build/web
```
then open http://127.0.0.1:8000 (pygbag looks for its packages on a local CDN when the page is served from `localhost`, so the address matters). pygbag packs only what is under `src/`, so the second line copies the pinned graphik release into `src/preponderous/` first, as `.github/workflows/browser.yml` does. `src/main.py` is the browser entry point; `src/tictactoe.py` stays the desktop one. Neither the build output in `src/build/` nor `src/preponderous/` is committed.

For the browser, every screen draws one frame per pass and yields to the event loop with `await asyncio.sleep(0)`, and the one-second pauses use `await asyncio.sleep(1)`, so the screens, the cell handlers and the win check are coroutines. A button is pressed by the left-button press event that lands on it, once per click or tap (a browser tap delivers its press and release in the same frame, so [graphik](https://github.com/Stephenson-Software/graphik)'s held-button check is not used for pressing). Presses made during the one-second pause before an end screen are discarded, because Play Again is drawn over the bottom-middle cell. Presses made during the computer's one-second pause are discarded too, so a tap is not played as the next move before the computer's mark has been seen. Presses made in the half second after Start is pressed are discarded as well, because Start is drawn over the centre cell and the second press of a double-click would otherwise play a move there.

## Getting Started
### Requirements
- Python 3
- [pygame](https://www.pygame.org/)
- [graphik](https://github.com/Stephenson-Software/graphik), installed by `pip install -r requirements.txt` from the release pinned there

### Installation
```
pip install -r requirements.txt
```

### Running the game
```
python3 src/tictactoe.py
```
On Linux and Windows this opens the 3D window when it can (see below) and otherwise says why in plain words and opens the 2D window. `--2d` always opens the 2D window; `--strata` insists on 3D and stops with the reason instead of falling back.

## 3D view
The desktop game can also be played in 3D, drawn with [Strata](https://github.com/Preponderous-Software/strata) through graphik's 3D grid view (`preponderous.graphik.grid3d`). It is the same game: the title screen, Start, the board, the computer's move after a one-second pause, the three end screens with Play Again and Quit, hover feedback on every button and cell, and the rule that presses made during a pause are dropped all come from `src/tictactoe.py` unchanged. The board is a 3x3 grid of tiles with an X or an O standing on each claimed cell; a click lands on the tile under the pointer, and the other buttons are drawn as panels in the same places as in the 2D window. Closing the window quits, as in 2D. Neither window binds any keys.

It needs a graphik release that includes the 3D grid view, and Strata's Python binding:
```
pip install "strata-engine @ git+https://github.com/Preponderous-Software/strata@v0.7.0#subdirectory=bindings/python"
```
The binding downloads Strata's library (pinned by SHA-256) the first time it runs. Strata ships Linux x64 and Windows x64 libraries, so there is no 3D view on macOS or in the browser build, which keeps the 2D window. `src/strata_view/` holds the view: `scene.py` maps the game and each screen's text and buttons to shapes and needs no GPU, and `game.py` runs the game's own screens in a Strata window. `python3 tools/strata_snapshot.py --out shots/` renders every screen headless to PNGs. The 3D tests under `tests/view3d/` are skipped where the installed graphik has no 3D grid view.

### Running the tests
The tests use [pytest](https://docs.pytest.org/) and run headlessly, so no display is required. They run the screens and handlers with `asyncio.run` and replace `asyncio.sleep`, so nothing actually waits.
```
pip install -r requirements-dev.txt
python3 -m pytest
```

## Continuous integration
`.github/workflows/ci.yml` runs the tests on every push to `master` and every pull request, then launches the game under the dummy SDL drivers to confirm it starts and keeps running.

`.github/workflows/browser.yml` runs on the same events and builds the browser version with pygbag, checking that `src/build/web/index.html` was produced. On a manual run (`workflow_dispatch`), or on a push to `master` once the repository variable `ARCADE_ENABLED` is `true`, it deploys the build to [arcade](https://github.com/Stephenson-Software/arcade) with [arcade-deploy](https://github.com/Stephenson-Software/arcade-deploy), as version `<version.txt>+g<short commit>`; the upload token is the `ARCADE_TOKEN` secret.

## Support
You can find the support discord server [here](https://discord.gg/49J4RHQxhy).

## Authors and acknowledgement
### Developers
Name | Main Contributions
------------ | -------------
Daniel Stephenson | Creator
