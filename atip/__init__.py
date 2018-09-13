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
from . import load_sim, sim_data_source, ease  # noqa: E402
"""Error 402 is suppressed as we cannot import these modules at the top of the
file as pytac and at must be added to the path first or the imports will fail.
"""
__all__ = ["load_sim", "sim_data_source", "ease", "tester"]
