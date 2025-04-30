import argparse
import asyncio
import logging
import os
import socket
from pathlib import Path
from warnings import warn

from aioca import CANothing, caget
from softioc import asyncio_dispatcher, builder, softioc

from . import atip_server

LOG_FORMAT = "%(asctime)s %(message)s"


DATADIR = Path(__file__).absolute().parent / "data"


def parse_arguments():
    """Parse command line arguments sent to virtac"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "ring_mode",
        nargs="?",
        type=str,
        help="The ring mode to be used, e.g., IO4 or DIAD",
    )
    parser.add_argument(
        "-d",
        "--disable-emittance",
        help="Disable the simulator's time-consuming emittance calculation",
        action="store_true",
    )
    parser.add_argument(
        "-t",
        "--enable-tfb",
        help="Simulate extra dummy hardware to be used by the Tune Feedback system",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Increase logging verbosity",
        action="store_true",
    )
    return parser.parse_args()


async def async_main():
    """Main entrypoint for virtac. Executed when running the 'virtac' command"""
    args = parse_arguments()
    loop = asyncio.get_event_loop()  # TODO: check a loop is running
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.getLogger().setLevel(log_level)

    # Determine the ring mode
    if args.ring_mode is not None:
        ring_mode = args.ring_mode
    else:
        try:
            ring_mode = str(os.environ["RINGMODE"])
        except KeyError:
            try:
                value = await caget("SR-CS-RING-01:MODE", timeout=0.5, format=2)
                ring_mode = value.enums[int(value)]
                logging.warning(
                    f"Ring mode not specified, using value from real "
                    f"machine as default: {value}"
                )
            except CANothing:
                ring_mode = "I04"
                logging.warning(f"Ring mode not specified, using default: {ring_mode}")

    # Create PVs.
    logging.debug("Creating ATIP server")
    server: atip_server.ATIPServer = await atip_server.ATIPServer.create(
        ring_mode,
        DATADIR / ring_mode / "limits.csv",
        DATADIR / ring_mode / "bba.csv",
        DATADIR / ring_mode / "feedback.csv",
        DATADIR / ring_mode / "mirrored.csv",
        DATADIR / ring_mode / "tunefb.csv",
        args.disable_emittance,
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
    dispatcher = asyncio_dispatcher.AsyncioDispatcher(loop=loop)
    builder.LoadDatabase()
    softioc.iocInit(dispatcher)
    server.monitor_mirrored_pvs()
    if args.enable_tfb:
        server.setup_tune_feedback()

    # context = globals() | {"server": server}
    # softioc.interactive_ioc(context)
    # Leaving the IOC in interactive mode can interfere with logging of
    # error messages, try commenting out the above line and uncommenting
    # the below to run without the interactive ioc shell.
    # TODO: Make interactive ioc work with logging
    while True:
        logging.debug("Sleeping")
        await asyncio.sleep(10)


def main():
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)-4s %(message)s",
        datefmt="%H:%M:%S",
    )
    # Load the AT sim into the Pytac lattice.
    asyncio.run(async_main())
