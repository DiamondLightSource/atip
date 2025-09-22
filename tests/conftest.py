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


@pytest.fixture(scope="function", params=["I04"])
def at_and_pytac_lattices(request):
    lattices = []
    lattices.append(load_csv.load(request.param, cs.ControlSystem()))
    lattices.append(atip.utils.load_at_lattice(request.param))
    return lattices


@pytest.fixture(scope="function", params=["I04"])
def pytac_lattice(request):
    return load_csv.load(request.param, cs.ControlSystem())


@pytest.fixture(scope="function", params=["I04"])
def at_lattice(request):
    return atip.utils.load_at_lattice(request.param)


@pytest.fixture(scope="function", params=["DIAD"])
def lattice_filepath(request):
    here = os.path.dirname(__file__)
    filepath = os.path.realpath(
        os.path.join(here, f"../src/atip/rings/{request.param}.mat")
    )
    return filepath


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
        "tune": numpy.array([0.1823785, 0.2730096]),
        "chromaticity": numpy.array([2.05528097, 2.90000203]),
        "closed_orbit": numpy.zeros((6, len(at_lattice))),
        "dispersion": numpy.array(
            [8.04285115e-02, 1.82229041e-03, -4.66599806e-16, 9.68514718e-17]
        ),
        "s_pos": numpy.cumsum(
            [0.0] + [getattr(elem, "Length", 0) for elem in at_lattice[:-1]]
        ),
        "alpha": numpy.array([0.41083373, 0.76826358]),
        "beta": numpy.array([11.41465744, 9.38580055]),
        "m66": numpy.array(
            [
                [
                    7.86384427e-01,
                    6.95380796e00,
                    0.00000000e00,
                    0.00000000e00,
                    -1.79313850e-03,
                    2.45580638e-05,
                ],
                [
                    -9.32748192e-02,
                    4.46416511e-01,
                    0.00000000e00,
                    0.00000000e00,
                    9.24467098e-03,
                    -5.27165562e-05,
                ],
                [0.0, 0.0, 0.61607674, 6.58807515, 0.0, 0.0],
                [0.0, 0.0, -0.16763406, -0.1699704, 0.0, 0.0],
                [
                    -1.51614014e-05,
                    -5.76481623e-05,
                    0.00000000e00,
                    0.00000000e00,
                    9.98875829e-01,
                    -8.01593240e-03,
                ],
                [0.00710922, 0.06512084, 0.0, 0.0, 0.08704729, 0.99976966],
            ]
        ),
        "mu": numpy.array([1.76647685e02, 8.27678865e01, 2.65364030e-02]),
        "emitXY": numpy.array([2.70982566e-09, 0.00000000e00]),
        "rad_int": numpy.array(
            [
                8.75420386e-02,
                8.65728946e-01,
                1.20198368e-01,
                -7.53876505e-03,
                1.78670458e-04,
            ]
        ),
    }
