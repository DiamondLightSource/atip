import os
import mock
import atip
import at
import pytest
import numpy


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
    return atip.sim_data_source.ATLatticeDataSource(mock.Mock())


@pytest.fixture()
def at_ring():
    ring = at.load.load_mat(os.path.join(os.path.realpath('../'),
                            'at/pyat/test_matlab/hmba.mat'))
    return ring


@pytest.fixture()
def mocked_ado(at_ring):
    base = numpy.ones((len(at_ring),4))
    ado = atip.sim_data_source.ATAcceleratorData(at_ring)
    ado._lattice = mock.PropertyMock(energy=5)
    ado._emittance = ([], [], {'emitXY': (base[:, :2] * numpy.array([1.4,
                                                                     0.45]))})
    ado._lindata = ([], [3.14, 0.12], [2, 1],
                    {'closed_orbit': (base * numpy.array([0.6, 57, 0.2, 9])),
                     'dispersion': (base * numpy.array([8.8, 1.7, 23, 3.5])),
                     's_pos': numpy.array([0.1 * (i + 1) for i in
                                           range(len(at_ring))]),
                     'alpha': (base[:, :2] * numpy.array([-0.03, 0.03])),
                     'beta': (base[:, :2] * numpy.array([9.6, 6])),
                     'm44': (numpy.ones((len(at_ring), 4, 4)) *
                             numpy.eye(4) * 0.8),
                     'mu': (base[:, :2] * numpy.array([176, 82]))})
    return ado
