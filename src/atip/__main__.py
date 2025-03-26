"""Atip entrypoint. This file currently does not do anything interesting, as atip is a
library and not really designed to be a runnable application."""

from argparse import ArgumentParser
from collections.abc import Sequence

import pytac

import atip
from atip import __version__

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

    lat = pytac.load_csv.load("DIAD")
    atip.load_sim.load_from_filepath(lat, "src/atip/rings/DIAD.mat")
    lat.set_default_data_source(pytac.SIM)
    print(lat.get_value("x"))
    hcor1 = lat.get_elements("HSTR")[0]
    hcor1.set_value("x_kick", 1, units=pytac.ENG)
    print(lat.get_value("x"))


if __name__ == "__main__":
    main()
