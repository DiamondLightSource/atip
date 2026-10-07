"""Interface for ``python -m atip``."""

import asyncio
import logging
from argparse import ArgumentParser

import atip

__all__ = ["main"]


async def async_main() -> None:
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


def main() -> None:
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    # Load the AT sim into the Pytac lattice.
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
