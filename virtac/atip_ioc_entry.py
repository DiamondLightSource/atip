import argparse
import logging
import os
from pathlib import Path
from warnings import warn

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

    # Warn if set to default EPICS port(s) accounting for env var inheritance/fallback.
    conflict_warning = ", this may lead to conflicting PV names on multiple servers."
    epics_env_vars = [
        "EPICS_CA_REPEATER_PORT",
        "EPICS_CAS_SERVER_PORT",
        "EPICS_CA_SERVER_PORT",
        "EPICS_CAS_BEACON_PORT",
    ]
    # Need 0 & 1 to both be set or just 2 set, but none of the others can be set wrong.
    if (
        bool(set(epics_env_vars[:2]) - os.environ.keys())
        or epics_env_vars[2] not in os.environ.keys()
    ):
        warn(
            "No EPICS port set, default base port (5064) will be used"
            + conflict_warning
        )
    ports_list = [int(os.environ.get(env_var, 0)) for env_var in epics_env_vars]
    if 5064 in ports_list:
        warn(
            "'EPICS_CA_SERVER_PORT' or 'EPICS_CAS_SERVER_PORT' is set to 5064"
            + conflict_warning
        )
    elif 5065 in ports_list:
        warn(
            "'EPICS_CA_REPEATER_PORT' or 'EPICS_CAS_BEACON_PORT' is set to 5065"
            + conflict_warning
        )

    # Start the IOC.
    builder.LoadDatabase()
    softioc.iocInit()
    server.monitor_mirrored_pvs()
    server.setup_tune_feedback()

    softioc.interactive_ioc(globals())
