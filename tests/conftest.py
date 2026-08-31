import os
import sys

# pygame must not open a real window or audio device when the tests import it,
# so the dummy drivers are selected before src/ is placed on the path.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
