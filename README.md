# Tic-Tac-Toe
This game allows you to play Tic Tac Toe against the computer.

## Play in your browser
The game is also built for the browser with [pygbag](https://pygame-web.github.io) and served at https://tic-tak-toe.play.danielstephenson.dev, alongside the other games at https://danielstephenson.dev/play. Nothing needs to be installed: the page loads Python and pygame compiled to WebAssembly, then asks for a click or tap to start. The board and buttons work with a mouse or a tap on a phone. There is no Quit button in the browser build (closing the tab is how to leave).

To build and serve it locally:
```
python3 -m pip install pygbag==0.9.3
python3 -m pygbag --build src
python3 -m http.server 8000 --bind 127.0.0.1 --directory src/build/web
```
then open http://127.0.0.1:8000 (pygbag looks for its packages on a local CDN when the page is served from `localhost`, so the address matters). `src/main.py` is the browser entry point; `src/tictactoe.py` stays the desktop one. The build output in `src/build/` is not committed.

For the browser, every screen draws one frame per pass and yields to the event loop with `await asyncio.sleep(0)`, and the one-second pauses use `await asyncio.sleep(1)`, so the screens, the cell handlers and the win check are coroutines. A button is pressed by the left-button press event that lands on it, once per click or tap (a browser tap delivers its press and release in the same frame, so the vendored `src/Graphik.py`'s held-button check is not used for pressing). Presses made during the one-second pause before an end screen are discarded, because Play Again is drawn over the bottom-middle cell.

## Getting Started
### Requirements
- Python 3
- [pygame](https://www.pygame.org/)

### Installation
```
pip install -r requirements.txt
```

### Running the game
```
python3 src/tictactoe.py
```

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
