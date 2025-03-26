"""Atip entrypoint. This file currently does not do anything interesting, as atip is a
library and not really designed to be a runnable application."""

from argparse import ArgumentParser
from collections.abc import Sequence

from . import __version__

__all__ = ["main"]


def main(args: Sequence[str] | None = None) -> None:
    """Argument parser for the CLI."""
    parser = ArgumentParser()
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )
    parser.parse_args(args)


if __name__ == "__main__":
    main()
