=================
ATIP Installation
=================

This guide is for linux and is based off the current structures of AT and
Pytac, if you find a mistake please raise an issue on ATIP's GitHub page.

Initial Setup and Installation
------------------------------

1. Download AT, Pytac and ATIP into the same directory [1]_::

    $ cd <source-directory>
    $ git clone https://github.com/atcollab/at.git
    $ git clone https://github.com/dls-controls/pytac.git
    $ git clone https://github.com/T-Nicholls/atip.git


2. Install AT [2]_, and run the tests to check that it works correctly::

    $ cd <source-directory>/at/pyat
    $ virtualenv --no-site-packages venv
    $ source venv/bin/activate
    $ pip install -r requirements.txt
    $ python setup.py develop
    $ python -m pytest test
    $ deactivate


3. Install Pytac [3]_, and run the tests to check that it works correctly::

    $ cd <source-directory>/pytac
    $ pipenv shell
    $ pip install -r requirements.txt
    $ python -m pytest
    $ exit


4. Install ATIP::

    $ cd <source-directory>/atip
    $ pipenv shell
    $ pip install -r requirements.txt
    $ python -m pytest



Footnotes
---------

.. [1] Your directory structure should look like::

 .<source-directory>
 .    |____atip
 .    |____pytac
 .    |____at
 .         |____pyat


.. [2] Taken from: `at/pyat/README.rst`


.. [3] Taken from: `pytac/docs/installation.rst`
