import os
import unittest.mock as mock
from typing import Any

import at
import numpy
import pytest
from pytac import cs, load_csv

import atip

# Prevent pytest from catching exceptions when debugging in vscode so that break on
# exception works correctly (see: https://github.com/pytest-dev/pytest/issues/7409)
if os.getenv("PYTEST_RAISE", "0") == "1":

    @pytest.hookimpl(tryfirst=True)
    def pytest_exception_interact(call: pytest.CallInfo[Any]):
        if call.excinfo is not None:
            raise call.excinfo.value
        else:
            raise RuntimeError(
                f"{call} has no exception data, an unknown error has occurred"
            )

    @pytest.hookimpl(tryfirst=True)
    def pytest_internalerror(excinfo: pytest.ExceptionInfo[Any]):
        raise excinfo.value


@pytest.fixture(scope="session")
def at_elem():
    e = at.elements.Drift(
        "D1",
        0.0,
        KickAngle=[0, 0],
        Frequency=0,
        k=0.0,
        PolynomA=[0, 0, 0, 0],
        PolynomB=[0, 0, 0, 0],
        BendingAngle=0.0,
    )
    return e


@pytest.fixture(scope="session")
def at_elem_preset():
    e = at.elements.Drift(
        "D1",
        0.5,
        KickAngle=[0.1, 0.01],
        k=-0.07,
        Frequency=500,
        PolynomA=[1.3, 13, 22, 90],
        PolynomB=[8, -0.07, 42, 1],
        BendingAngle=0.13,
    )
    return e


@pytest.fixture(scope="session")
def atlds():
    return atip.sim_data_sources.ATLatticeDataSource(mock.Mock())


@pytest.fixture()
def at_lattice():
    return atip.utils.load_at_lattice("HMBA")


@pytest.fixture(scope="session")
def pytac_lattice():
    return load_csv.load("DIAD", cs.ControlSystem())


@pytest.fixture(scope="session")
def mat_filepath():
    here = os.path.dirname(__file__)
    return os.path.realpath(os.path.join(here, "../src/atip/rings/DIAD.mat"))


@pytest.fixture(scope="session")
def at_diad_lattice(mat_filepath):
    return at.load.load_mat(mat_filepath)


@pytest.fixture()
def atsim(at_lattice):
    return atip.simulator.ATSimulator(at_lattice)


@pytest.fixture()
def mocked_atsim(at_lattice):
    length = len(at_lattice) + 1
    base = numpy.ones((length, 4))
    atsim = atip.simulator.ATSimulator(at_lattice)
    atsim._at_lat = mock.PropertyMock(energy=5, circumference=(length * 0.1))
    emitdata = [{"emitXY": numpy.array([1.4, 0.45])}]
    twiss = {
        "closed_orbit": (base * numpy.array([0.6, 57, 0.2, 9])),
        "dispersion": (base * numpy.array([8.8, 1.7, 23, 3.5])),
        "s_pos": numpy.array([0.1 * (i + 1) for i in range(length)]),
        "alpha": (base[:, :2] * numpy.array([-0.03, 0.03])),
        "beta": (base[:, :2] * numpy.array([9.6, 6])),
        "M": (numpy.ones((length, 6, 6)) * (numpy.eye(6) * 0.8)),
        "mu": (base[:, :2] * numpy.array([176, 82])),
    }
    radint = (1.0, 2.0, 3.0, 4.0, 5.0)
    lattice_data = atip.simulator.LatticeData(
        twiss, [3.14, 0.12], [2, 1], emitdata, radint
    )
    atsim._lattice_data = lattice_data
    return atsim


@pytest.fixture()
def ba_atsim(at_lattice):
    dr = at.elements.Drift("d1", 1)
    dr.BendingAngle = 9001
    lat = [at.elements.Dipole("b1", 1, 1.3), at.elements.Dipole("b2", 1, -0.8)]
    at_sim = atip.simulator.ATSimulator(at_lattice)
    at_sim._at_lat = lat
    return at_sim


@pytest.fixture()
def initial_phys_data(at_lattice):
    return {
        "tune": numpy.array([0.38156245, 0.85437543]),
        "chromaticity": numpy.array([0.17919002, 0.12242263]),
        "closed_orbit": numpy.zeros((6, len(at_lattice))),
        "dispersion": numpy.array(
            [1.72682010e-3, 4.04368254e-9, 5.88659608e-28, -8.95277691e-29]
        ),
        "s_pos": numpy.cumsum(
            [0.0] + [getattr(elem, "Length", 0) for elem in at_lattice[:-1]]
        ),
        "alpha": numpy.array([0.384261343, 1.00253822]),
        "beta": numpy.array([7.91882634, 5.30280084]),
        "m66": numpy.array(
            [
                [-0.47537132, 6.62427828, 0.0, 0.0, 2.55038448e-03, -5.33885495e-07],
                [-0.09816788, -0.73565385, 0.0, 0.0, 1.69015229e-04, -3.53808533e-08],
                [0.0, 0.0, -0.18476435, -3.7128728, 0.0, 0.0],
                [0.0, 0.0, 0.29967874, 0.60979916, 0.0, 0.0],
                [
                    1.24684834e-06,
                    2.15443495e-05,
                    0.0,
                    0.0,
                    9.99980691e-01,
                    2.09331256e-04,
                ],
                [
                    1.70098195e-04,
                    2.99580152e-03,
                    0.0,
                    0.0,
                    2.24325864e-03,
                    9.99999530e-01,
                ],
            ]
        ),
        "mu": numpy.array([14.59693301, 4.58153046, 6.85248778e-04]),
        "emitXY": numpy.array([1.32528e-10, 0.0]),
        "rad_int": numpy.array(
            [
                2.2435734416179783e-3,
                4.3264360771244244e-3,
                1.049245018317141e-4,
                -2.3049140720439194e-3,
                1.6505019559193616e-8,
            ]
        ),
    }
