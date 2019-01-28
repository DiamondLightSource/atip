import os

import at
import mock
import numpy
import pytest

import atip


@pytest.fixture()
def at_elem():
    e = at.elements.Drift('D1', 0.0, KickAngle=[0, 0], Index=1, Frequency=0,
                          k=0.0, PolynomA=[0, 0, 0, 0], PolynomB=[0, 0, 0, 0])
    return e


@pytest.fixture()
def at_elem_preset():
    e = at.elements.Drift('D1', 0.5, KickAngle=[0.1, 0.01], Index=6, k=-0.07,
                          Frequency=500, PolynomA=[1.3, 13, 22, 90],
                          PolynomB=[8, -0.07, 42, 1])
    return e


@pytest.fixture()
def atlds():
    return atip.sim_data_sources.ATLatticeDataSource(mock.Mock())


@pytest.fixture()
def at_lattice():
    ring = at.load.load_mat(os.path.join(os.path.realpath('../'),
                            'at/pyat/test_matlab/hmba.mat'))
    lattice = at.lattice_object.Lattice(ring)
    return lattice


@pytest.fixture()
def mocked_atsim(at_lattice):
    base = numpy.ones((len(at_lattice), 4))
    atsim = atip.at_interface.ATSimulator(at_lattice)
    atsim._lattice = mock.PropertyMock(energy=5)
    atsim._emittance = ([], [],
                        {'emitXY': (base[:, :2] * numpy.array([1.4, 0.45]))})
    atsim._lindata = ([], [3.14, 0.12], [2, 1],
                      {'closed_orbit': (base * numpy.array([0.6, 57, 0.2, 9])),
                       'dispersion': (base * numpy.array([8.8, 1.7, 23, 3.5])),
                       's_pos': numpy.array([0.1 * (i + 1) for i in
                                             range(len(at_lattice))]),
                       'alpha': (base[:, :2] * numpy.array([-0.03, 0.03])),
                       'beta': (base[:, :2] * numpy.array([9.6, 6])),
                       'm44': (numpy.ones((len(at_lattice), 4, 4)) *
                               numpy.eye(4) * 0.8),
                       'mu': (base[:, :2] * numpy.array([176, 82]))})
    return atsim


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
                                  [0., 0., -0.18476435, -3.7128728 ],
                                  [0., 0., 0.29967874, 0.60979916]]]),
             'mu': numpy.array([[14.59693301, 4.58153046]])})
