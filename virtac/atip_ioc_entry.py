import argparse
import logging
import os
from pathlib import Path

import epicscorelibs.path.cothread  # noqa
from cothread.catools import ca_nothing, caget
from softioc import builder, softioc

from . import atip_server

LOG_FORMAT = "%(asctime)s %(message)s"


DATADIR = Path(__file__).absolute().parent / "data"


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("ring_mode", nargs="?", type=str, help="Ring mode name")
    parser.add_argument(
        "--disable-emittance", "-d", help="disable emittance calc", action="store_true"
    )
    parser.add_argument(
        "--verbose", "-v", help="increase output verbosity", action="store_true"
    )
    return parser.parse_args()


def main():

    args = parse_arguments()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format=LOG_FORMAT)

    # Determine the ring mode
    if args.ring_mode is not None:
        ring_mode = args.ring_mode
    else:
        try:
            ring_mode = str(os.environ["RINGMODE"])
        except KeyError:
            try:
                value = caget("SR-CS-RING-01:MODE", format=2)
                ring_mode = value.enums[int(value)]
            except ca_nothing:
                ring_mode = "I04"

    # Create PVs.
    server = atip_server.ATIPServer(
        ring_mode,
        DATADIR / "limits.csv",
        DATADIR / "feedback.csv",
        DATADIR / "mirrored.csv",
        DATADIR / "tunefb.csv",
        not args.disable_emittance,
    )

    # Add special case out record for SOFB to write to.
    builder.SetDeviceName("CS-CS-MSTAT-01")
    builder.aOut("FBHEART", initial_value=10)

    # Start the IOC.
    builder.LoadDatabase()
    softioc.iocInit()
    server.monitor_mirrored_pvs()
    server.setup_tune_feedback()

    softioc.interactive_ioc(globals())
