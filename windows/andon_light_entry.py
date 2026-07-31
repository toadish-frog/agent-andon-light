"""PyInstaller entry point. Not part of the andon_light package itself —
PyInstaller needs a plain script (not a relative-import module) to point at."""

import sys

from andon_light.cli import main

if __name__ == "__main__":
    sys.exit(main())
