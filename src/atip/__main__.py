"""Interface for ``python -m atip``."""

import asyncio
import logging
import random
from argparse import ArgumentParser
from collections.abc import Sequence

import pytac

import atip

from . import __version__

__all__ = ["main"]


async def async_main(args: Sequence[str] | None = None) -> None:
    """Argument parser for the CLI."""
    parser = ArgumentParser()
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )
    parser.add_argument(
        "-t",
        "--run-test",
        help="Start an endless test of atip",
        action="store_true",
    )
    args = parser.parse_args()

    if args.run_test:
        # Load the DIAD lattice from Pytac.
        lat = await pytac.load_csv.load("DIAD")
        await atip.load_sim.load_from_filepath(lat, "../atip/src/atip/rings/DIAD.mat")
        # Use the sim by default.
        lat.set_default_data_source(pytac.SIM)
        # The initial beam position is zero.
        print(await lat.get_value("x"))

        # Get the first horizontal corrector magnet and set its current to 1A.
        hcor1 = lat.get_elements("HSTR")[0]
        while True:
            kick: float = random.uniform(0, 2)
            print(f"Applying x_kick of {kick}")
            await hcor1.set_value("x_kick", kick, units=pytac.ENG)
            # Now the x beam position has changed.
            print(f"New data: {await lat.get_value('x')}")
            await asyncio.sleep(1)


def main(args: Sequence[str] | None = None) -> None:
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    # Load the AT sim into the Pytac lattice.
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
