import logging
import os
import sys
from pathlib import Path

from . import atip_server
from softioc import builder, softioc
from cothread.catools import caget, ca_nothing

LOG_FORMAT = "%(asctime)s %(message)s"


DATADIR = Path(__file__).absolute().parent / "data"


def main():
    if "-v" in sys.argv:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
        sys.argv.remove("-v")
    else:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    # Determine the ring mode
    if sys.argv[1:]:
        ring_mode = sys.argv[1]
    else:
        try:
            ring_mode = str(os.environ["RINGMODE"])
        except KeyError:
            try:
                value = caget("SR-CS-RING-01:MODE", format=2)
                ring_mode = value.enums[int(value)]
            except ca_nothing:
                ring_mode = "DIAD"

    # Create PVs.
    server = atip_server.ATIPServer(
        ring_mode,
        DATADIR / "limits.csv",
        DATADIR / "feedback.csv",
        DATADIR / "mirrored.csv",
        DATADIR / "tunefb.csv",
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
