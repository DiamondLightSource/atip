"""ATIP: Accelerator Toolbox Interface for Pytac.

Reqs:
    AT, Pytac and ATIP all installed in the same source directory.
    pipenv install --dev
    pipenv shell
    pip install numpy
    pip install scipy
    pip install pytest
    pip install cothread
"""
# Add AT & Pytac to path.
import sys
import os
source_directory = os.path.realpath('../')
sys.path.append(source_directory+'/pytac')
sys.path.append(source_directory+'/at/pyat/build/lib.linux-x86_64-2.7')

# Initialise all modules.
import pytac, at  # noqa: E401,F401
from . import load_sim, SimDataSource, ease  # noqa: E402,F401
