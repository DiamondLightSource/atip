"""virtac: a python based virtual accelerator using ATIP.
See README.rst & FEEDBACK_SYSTEMS.rst for more information.

.. data:: __version__
    :type: str

    Version number as calculated by https://github.com/pypa/setuptools_scm
"""

from atip._version import __version__

from . import __main__, atip_server, create_csv, masks, mirror_objects

__all__ = [
    "__version__",
    "__main__",
    "atip_server",
    "create_csv",
    "masks",
    "mirror_objects",
]
