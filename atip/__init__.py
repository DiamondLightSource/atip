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
import os
import sys
source_dir = os.path.realpath('../')
sys.path.append(os.path.join(source_dir, 'at/pyat'))
sys.path.append(os.path.join(source_dir, 'pytac'))
sys.path.append(os.path.join(source_dir, 'atip/atip'))  # fix for python3


# Initialise all modules.
from . import load_sim, sim_data_source, ease  # noqa: E402
"""Error 402 is suppressed as we cannot import these modules at the top of the
file as pytac and at must be added to the path first or the imports will fail.
"""
__all__ = ["load_sim", "sim_data_source", "ease"]
