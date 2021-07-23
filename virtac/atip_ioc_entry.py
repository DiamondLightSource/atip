import logging
import os
import sys
from pathlib import Path

from . import atip_server
from softioc import builder, softioc
from cothread.catools import caget, ca_nothing

LOG_FORMAT = '%(asctime)s %(message)s'


here = Path(__file__).absolute().parent


def main():
    if '-v' in sys.argv:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
        sys.argv.remove('-v')
    else:
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    # Determine the ring mode
    if sys.argv[1:]:
        ring_mode = sys.argv[1]
    else:
        try:
            ring_mode = str(os.environ['RINGMODE'])
        except KeyError:
            try:
                value = caget('SR-CS-RING-01:MODE', format=2)
                ring_mode = value.enums[int(value)]
            except ca_nothing:
                ring_mode = 'DIAD'

    # Create PVs.
    server = atip_server.ATIPServer(
        ring_mode,
        here / 'limits.csv',
        here / 'feedback.csv',
        here / 'mirrored.csv',
        here / 'tunefb.csv'
    )

    # Add special case out record for SOFB to write to.
    builder.SetDeviceName('CS-CS-MSTAT-01')
    builder.aOut('FBHEART', initial_value=10)

    # Start the IOC.
    builder.LoadDatabase()
    softioc.iocInit()
    server.monitor_mirrored_pvs()

    softioc.interactive_ioc(globals())
