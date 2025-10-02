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
    return atip.utils.load_at_lattice("I04")


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
def initial_phys_data(atsim):
    return {
        "tune": numpy.array([atsim.get_tune("x"), atsim.get_tune("y")]),
        "chromaticity": numpy.array(
            [atsim.get_chromaticity("x"), atsim.get_chromaticity("y")]
        ),
        "closed_orbit": numpy.zeros((6, len(atsim._at_lat))),
        "dispersion": atsim.get_dispersion()[-1],
        "s_pos": numpy.cumsum(
            [0.0] + [getattr(elem, "Length", 0) for elem in atsim._at_lat[:-1]]
        ),
        "alpha": atsim.get_alpha()[-1],
        "beta": atsim.get_beta()[-1],
        "m66": atsim.get_m66()[-1],
        "mu": atsim.get_mu()[-1],
        "emitXY": numpy.array([atsim.get_emittance("x"), atsim.get_emittance("y")]),
        "rad_int": atsim.get_radiation_integrals(),
    }
