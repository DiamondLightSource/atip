"""ATIP: Accelerator Toolbox Interface for Pytac.
See README.rst & INSTALL.rst for more information.

.. data:: __version__
    :type: str

    Version number as calculated by https://github.com/pypa/setuptools_scm
"""

from ._version import __version__

from . import load_sim, sim_data_sources, simulator, utils

__all__ = ["__version__", "load_sim", "sim_data_sources", "simulator", "utils"]
