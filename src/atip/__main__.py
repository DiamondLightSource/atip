"""Interface for ``python -m atip``."""

import asyncio
import logging
from argparse import ArgumentParser
from collections.abc import Sequence

import pytac

import atip

__all__ = ["main"]


async def async_main(args: Sequence[str] | None = None) -> None:
    """Argument parser for the CLI."""
    parser = ArgumentParser()
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=atip.__version__,
    )
    parser.add_argument(
        "-t",
        "--run-test",
        help="Start an endless test of atip",
        action="store_true",
    )
    args = parser.parse_args()

    if args.run_test:
        await atip.utils.test_atip()


def main(args: Sequence[str] | None = None) -> None:
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    # Load the AT sim into the Pytac lattice.
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
