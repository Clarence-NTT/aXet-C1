"""Module entry point for python -m logscope.cli compatibility."""

from logscope.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
