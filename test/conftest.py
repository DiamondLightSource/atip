import os

import at
import mock
import numpy
import pytest
from pytac import load_csv, cs

import atip


@pytest.fixture(scope='session')
def at_elem():
    e = at.elements.Drift('D1', 0.0, KickAngle=[0, 0], Frequency=0, k=0.0,
                          PolynomA=[0, 0, 0, 0], PolynomB=[0, 0, 0, 0],
                          BendingAngle=0.0)
    return e


@pytest.fixture(scope='session')
def at_elem_preset():
    e = at.elements.Drift('D1', 0.5, KickAngle=[0.1, 0.01], k=-0.07,
                          Frequency=500, PolynomA=[1.3, 13, 22, 90],
                          PolynomB=[8, -0.07, 42, 1], BendingAngle=0.13)
    return e


@pytest.fixture(scope='session')
def atlds():
    return atip.sim_data_sources.ATLatticeDataSource(mock.Mock())


@pytest.fixture()
def at_lattice():
    return atip.utils.load_at_lattice('HMBA')


@pytest.fixture(scope='session')
def pytac_lattice():
    return load_csv.load('DIAD', cs.ControlSystem())


@pytest.fixture(scope='session')
def mat_filepath():
    here = os.path.dirname(__file__)
    return os.path.realpath(os.path.join(here, '../atip/rings/diad.mat'))


@pytest.fixture(scope='session')
def at_diad_lattice(mat_filepath):
    return at.load.load_mat(mat_filepath)


@pytest.fixture()
def atsim(at_lattice):
    return atip.simulator.ATSimulator(at_lattice)


@pytest.fixture()
def mocked_atsim(at_lattice):
    length = len(at_lattice)+1
    base = numpy.ones((length, 4))
    r66 = numpy.zeros((6, 6))
    r66[4, 4] = 16
    atsim = atip.simulator.ATSimulator(at_lattice)
    atsim._at_lat = mock.PropertyMock(energy=5, energy_loss=73)
    atsim._at_lat.get_mcf.return_value = 42
    atsim._at_lat.get_s_pos.return_value = numpy.array([0.1 * (i + 1) for i in
                                                        range(length)])
    atsim._emitdata = ({'r66': r66,
                        'emitXY': numpy.array([1.4, 0.45])},
                       {'damping_rates': [13, 3, 7]})
    atsim._lindata = ([], [3.14, 0.12], [2, 1],
                      {'closed_orbit': (base * numpy.array([0.6, 57, 0.2, 9])),
                       'dispersion': (base * numpy.array([8.8, 1.7, 23, 3.5])),
                       's_pos': numpy.array([0.1 * (i + 1) for i in
                                             range(length)]),
                       'alpha': (base[:, :2] * numpy.array([-0.03, 0.03])),
                       'beta': (base[:, :2] * numpy.array([9.6, 6])),
                       'm44': (numpy.ones((length,
                                           4, 4)) * (numpy.eye(4) * 0.8)),
                       'mu': (base[:, :2] * numpy.array([176, 82]))})
    return atsim


@pytest.fixture()
def ba_atsim(at_lattice):
    dr = at.elements.Drift('d1', 1)
    dr.BendingAngle = 9001
    lat = [at.elements.Dipole('b1', 1, 1.3), at.elements.Dipole('b2', 1, -0.8)]
    at_sim = atip.simulator.ATSimulator(at_lattice)
    at_sim._at_lat = lat
    return at_sim


@pytest.fixture()
def initial_emit(at_lattice):
    return ([], [], {'emitXY':
                     numpy.ones((len(at_lattice), 2)) * [1.32528e-10, 0.]})


@pytest.fixture()
def initial_lin(at_lattice):
    return ([], [0.38156245, 0.85437543], [0.17919002, 0.12242263],
            {'closed_orbit': numpy.zeros((len(at_lattice), 6)),
             'dispersion': numpy.array([[1.72682010e-3, 4.04368254e-9,
                                         5.88659608e-28, -8.95277691e-29]]),
             's_pos': numpy.cumsum([0.0] + [getattr(elem, 'Length', 0) for elem
                                            in at_lattice[:-1]]),
             'alpha': numpy.array([[0.384261343, 1.00253822]]),
             'beta': numpy.array([[7.91882634, 5.30280084]]),
             'm44': numpy.array([[[-0.47537132, 6.62427828, 0., 0.],
                                  [-0.09816788, -0.73565385, 0., 0.],
                                  [0., 0., -0.18476435, -3.7128728],
                                  [0., 0., 0.29967874, 0.60979916]]]),
             'mu': numpy.array([[14.59693301, 4.58153046]])})
