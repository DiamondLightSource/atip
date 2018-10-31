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
import subprocess
source_directory = os.path.realpath('../')
python_version = sys.version[:3]
os.environ['PYTHONPATH'] = source_directory+"/atip/at_installation"
process = subprocess.Popen(['python', 'setup.py', 'build', '--build-base='+source_directory+'/atip/at_installation'], cwd=source_directory+'/at/pyat')  # Don't try this at home!
process.wait()
sys.path.append(source_directory+'/atip/at_installation/lib.linux-x86_64-'+python_version)
sys.path.append(source_directory+'/pytac')
sys.path.append(source_directory+'/atip/atip')  # fix for mypython3


# Initialise all modules.
from . import load_sim, sim_data_source, ease  # noqa: E402
"""Error 402 is suppressed as we cannot import these modules at the top of the
file as pytac and at must be added to the path first or the imports will fail.
"""
__all__ = ["load_sim", "sim_data_source", "ease", "tester"]
