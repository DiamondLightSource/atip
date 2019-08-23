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
    $ git clone https://github.com/dls-controls/atip.git

2. Create a pipenv and install the dependencies::

    $ cd atip
    $ pipenv install --dev
    $ pipenv shell

3. Build AT's .so files::

    $ cd ../at/pyat
    $ python setup.py develop

4. Run the tests to ensure all modules are working correctly::

    $ python -m pytest test
    $ cd ../../pytac
    $ python -m pytest
    $ cd ../atip
    $ python -m pytest

Troubleshooting
---------------

If you encounter problems with your pyAT installation, please refer to 
``pyat/README.rst`` in the ``at`` source directory. Help for installing
Pytac is available on `Readthedocs
<https://pytac.readthedocs.io/en/latest/examples.html#installation>`_.

Please note that for ATIP to function with Python 3.7 or later, you must
use Cothread>=2.16.

Footnotes
---------

.. [1] Your directory structure should look like::

 .<source-directory>
 .    |____atip
 .    |____pytac
 .    |____at
 .         |____pyat
