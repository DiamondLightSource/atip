import argparse
import logging
import os
import socket
from pathlib import Path
from warnings import warn

import epicscorelibs.path.cothread  # noqa
from cothread.catools import ca_nothing, caget
from softioc import builder, softioc

from . import atip_server

LOG_FORMAT = "%(asctime)s %(message)s"


DATADIR = Path(__file__).absolute().parent / "data"


def parse_arguments():
    """Parse command line arguments sent to virtac"""
    parser = argparse.ArgumentParser()
    parser.add_argument("ring_mode", nargs="?", type=str, help="Ring mode name")
    parser.add_argument(
        "--disable-emittance",
        "-d",
        help="disable the simulator's time-consuming emittance calculation",
        action="store_true",
    )
    parser.add_argument(
        "--enable-tfb",
        "-t",
        help="simulate extra dummy hardware to be used by the Tune Feedback system",
        action="store_true",
    )
    parser.add_argument(
        "--verbose", "-v", help="increase output verbosity", action="store_true"
    )
    return parser.parse_args()


def main():
    """Main entrypoint for virtac. Executed when running the 'virtac' command"""
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
        DATADIR / ring_mode / "limits.csv",
        DATADIR / ring_mode / "feedback.csv",
        DATADIR / ring_mode / "mirrored.csv",
        DATADIR / ring_mode / "tunefb.csv",
        not args.disable_emittance,
    )

    # Warn if set to default EPICS port(s) as this will likely cause PV conflicts.
    conflict_warning = ", this may lead to conflicting PV names with production IOCs."
    epics_env_vars = [
        "EPICS_CA_REPEATER_PORT",
        "EPICS_CAS_SERVER_PORT",
        "EPICS_CA_SERVER_PORT",
        "EPICS_CAS_BEACON_PORT",
    ]
    ports_list = [int(os.environ.get(env_var, 0)) for env_var in epics_env_vars]
    if 5064 in ports_list or 5065 in ports_list:
        warn(
            f"At least one of {epics_env_vars} is set to 5064 or 5065"
            + conflict_warning,
            stacklevel=1,
        )
    elif all(port == 0 for port in ports_list):
        warn(
            "No EPICS port set, default base port (5064) will be used"
            + conflict_warning,
            stacklevel=1,
        )
    # Avoid PV conflict between multiple IP interfaces on the same machine.
    primary_ip = socket.gethostbyname(socket.getfqdn())
    if "EPICS_CAS_INTF_ADDR_LIST" in os.environ.keys():
        warn(
            "Pre-existing 'EPICS_CAS_INTF_ADDR_LIST' value" + conflict_warning,
            stacklevel=1,
        )
    else:
        os.environ["EPICS_CAS_INTF_ADDR_LIST"] = primary_ip
        os.environ["EPICS_CAS_BEACON_ADDR_LIST"] = primary_ip
        os.environ["EPICS_CAS_AUTO_BEACON_ADDR_LIST"] = "NO"

    # Start the IOC.
    builder.LoadDatabase()
    softioc.iocInit()
    server.monitor_mirrored_pvs()
    if args.enable_tfb:
        server.setup_tune_feedback()

    softioc.interactive_ioc(globals())
