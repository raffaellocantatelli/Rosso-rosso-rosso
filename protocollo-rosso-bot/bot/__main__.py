"""Permette 'python -m bot' oltre a 'python -m bot.main'."""

from .main import main

if __name__ == "__main__":
    raise SystemExit(main())
