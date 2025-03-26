[![CI](https://github.com/DiamondLightSource/atip/actions/workflows/ci.yml/badge.svg)](https://github.com/DiamondLightSource/atip/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/DiamondLightSource/atip/branch/main/graph/badge.svg)](https://codecov.io/gh/DiamondLightSource/atip)
[![PyPI](https://img.shields.io/pypi/v/atip.svg)](https://pypi.org/project/atip)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)


# ATIP - Accelerator Toolbox Interface for Pytac

ATIP is an addition to  [Pytac](<https://github.com/DiamondLightSource/pytac>),
a framework for controlling particle accelerators. ATIP adds a simulator to
Pytac, which can be used and addressed in the same way as a real accelerator.

ATIP enables the easy offline testing of high level accelerator
controls applications, by either of two methods:

* By replacing the real accelerator at the point where it is addressed by the
  software, in the Pytac lattice object;

* In a standalone application as a "virtual accelerator", publishing the same
  control system interface as the live machine. At Diamond Light Source this
  has been implemented with EPICS, and run on a different port to the
  operational control system. So the only change required to test software is
  to configure this EPICS port.

The python implementation of
[Accelerator Toolbox](<https://github.com/atcollab/at>) (pyAT) is used for the
simulation.

Source          | <https://github.com/DiamondLightSource/atip>
:---:           | :---:
PyPI            | `pip install atip`
Docker          | `docker run ghcr.io/diamondlightsource/atip:latest`
Documentation   | <https://diamondlightsource.github.io/atip>
Installation    | <https://diamondlightsource.github.io/atip/tutorials/installation>
Releases        | <https://github.com/DiamondLightSource/atip/releases>

<!-- README only content. Anything below this line won't be included in index.md -->
