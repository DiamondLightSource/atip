=================
ATIP Installation
=================

This guide is for Linux and is based on the current structures of AT and Pytac,
if you find a mistake anywhere in ATIP please raise an issue on ATIP's GitHub
page, `here. <https://github.com/DiamondLightSource/atip>`_

Initial Setup and Installation
------------------------------

**Option 1: Install ATIP using pip**::

    $ pip install atip

**Option 2: Install ATIP from GitHub**:

1. Clone ATIP::

    $ cd <source-directory>
    $ git clone https://github.com/DiamondLightSource/atip.git

2. From within a python virtual environment, install the dependencies::

    $ cd atip
    $ pip install -e ./

3. Run the tests to ensure everything is working correctly::

    $ python -m pytest

Troubleshooting
---------------

Please note that for ATIP to function with Python 3.7 or later, you must
use Cothread>=2.16.
