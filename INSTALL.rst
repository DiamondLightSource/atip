=================
ATIP Installation
=================

This guide is for Linux and is based on the current structures of AT and Pytac,
if you find a mistake anywhere in ATIP please raise an issue on ATIP's GitHub
page, `here. <https://github.com/dls-controls/atip>`_

Initial Setup and Installation
------------------------------

**Option 1: Install ATIP using pip**::

    $ pip install atip

**Option 2: Install AT, Pytac and ATIP from GitHub**:

1. Download AT, Pytac and ATIP into the same directory [1]_::

    $ cd <source-directory>
    $ git clone https://github.com/atcollab/at.git
    $ git clone https://github.com/dls-controls/pytac.git
    $ git clone https://github.com/T-Nicholls/atip.git

2. Create a virtual enviroment and install the dependencies::

    $ cd atip
    $ virtualenv --no-site-packages venv
    $ source venv/bin/activate
    $ pip install -r requirements

3. Build AT's .so files::

    $ cd ../at/pyat
    $ python setup.py develop

4. Run the tests to ensure all modules are working correctly::

    $ python -m pytest test
    $ cd ../../pytac
    $ python -m pytest
    $ cd ../atip
    $ python -m pytest

Footnotes
---------

.. [1] Your directory structure should look like::

 .<source-directory>
 .    |____atip
 .    |____pytac
 .    |____at
 .         |____pyat
