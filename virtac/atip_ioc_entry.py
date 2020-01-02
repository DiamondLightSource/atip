import logging
import os
import sys

from pkg_resources import require

require('cothread')
require('pytac>=0.3.0')
require('accelerator-toolbox>=0.0.2')
require('epicsdbbuilder')
require('numpy>=1.10')
require('scipy>=0.16')
here = os.path.realpath(os.path.dirname(__file__))
sys.path.append(os.path.split(here)[0])

import atip_server  # noqa: E402
from softioc import builder, softioc  # noqa: E402
from cothread.catools import caget, ca_nothing  # noqa: E402
"""Error 402 from pycodestyle is suppressed as we cannot import these modules
at the top of the file as they must be below the requires and the path editing.
"""

LOG_FORMAT = '%(asctime)s %(message)s'

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
server = atip_server.ATIPServer(ring_mode, os.path.join(here, 'limits.csv'),
                                os.path.join(here, 'feedback.csv'),
                                os.path.join(here, 'mirrored.csv'),
                                os.path.join(here, 'tunefb.csv'))

# Add special case out record for SOFB to write to.
builder.SetDeviceName('CS-CS-MSTAT-01')
builder.aOut('FBHEART', initial_value=10)

# Start the IOC.
builder.LoadDatabase()
softioc.iocInit()
server.monitor_mirrored_pvs()

softioc.interactive_ioc(globals())
