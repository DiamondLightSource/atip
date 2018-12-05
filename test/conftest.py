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


@pytest.fixture()
def initial_emit(at_ring):
    return ([], [],
            {'emitXY': numpy.ones((len(at_ring) + 1, 2)) * [1.32528e-10, 0.]})

@pytest.fixture()
def initial_lin(at_ring):
    return ([], [0.38156245, 0.85437543], [0.17919002, 0.12242263],
            {'closed_orbit': numpy.zeros((len(at_ring) + 1, 6)),
             'dispersion': numpy.array([[1.72683082e-3, 4.04368253e-9,
                                         3.51285681e-28, -8.95277691e-29]]),
             's_pos': numpy.cumsum([0.0] + [getattr(elem, 'Length', 0) for elem
                                            in at_ring]),
             'alpha': numpy.array([[1.59491386e-07, -2.97115147e-6]]),
             'beta': numpy.array([[6.8999954, 2.64467888]]),
             'm44': numpy.array([[[-0.73565363, 4.67376566, 0., 0.],
                                  [-0.09816788, -0.73565385, 0., 0.],
                                  [0., 0., 0.60980387, -2.09605131],
                                  [0., 0., 0.29967874, 0.60979916]]]),
             'mu': numpy.array([[14.96379821, 5.36819914]])})
