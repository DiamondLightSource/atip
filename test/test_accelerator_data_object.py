import mock
import atip
import at
import pytac
import pytest
import numpy
from atip.sim_data_source import ATAcceleratorData


def test_accelerator_data_object_creation(at_ring):
    ado = ATAcceleratorData(at_ring)
    # Check inital state of flags.
    assert ado.new_changes.is_set() == False
    assert ado._paused.is_set() == False
    assert ado._running.is_set() == False
    # Check emittance and lindata are initially calculated.
    # How though?
#    for emit in ado._emittance:
#        assert isinstance(emit, numpy.ndarray)
#        assert all(numpy.array(emit.shape, dtype=bool)) == True
#    assert isinstance(ado._lindata, numpy.ndarray)
#    assert all(numpy.array(ado._lindata.shape, dtype=bool)) == True


def test_start_and_stop_thread(at_ring):
    ado = ATAcceleratorData(at_ring)
    assert ado._running.is_set() == False
    assert ado._calculation_thread.is_alive() == False
    ado.start_thread()
    with pytest.raises(RuntimeError):
        ado.start_thread()
    assert ado._running.is_set() == True
    assert ado._calculation_thread.is_alive() == True
    ado.stop_thread()
    assert ado._running.is_set() == False
    assert ado._calculation_thread.is_alive() == False


def test_recalculate_phys_data():
    # Potential to compare to hard-coded values for a known lattice.
    pass


def test_toggle_calculations(at_ring):
    ado = ATAcceleratorData(at_ring)
    assert ado._paused.is_set() == False
    ado.toggle_calculations()
    assert ado._paused.is_set() == True
    ado.toggle_calculations()
    assert ado._paused.is_set() == False
    # Possiblity to test it in practice:
    # pause > make a change > check no calc > unpause > check calc


def test_get_element():
    pass


def test_get_ring():
    pass


def test_get_lattice_object():
    pass


def test_get_chrom(mocked_ado):
    assert mocked_ado.get_chrom(0) == 2
    assert mocked_ado.get_chrom(1) == 1


def test_get_emit(mocked_ado):
    assert mocked_ado.get_emit(0) == 1.4
    assert mocked_ado.get_emit(1) == 0.45


def test_get_orbit(mocked_ado, at_ring):
    numpy.testing.assert_almost_equal(mocked_ado.get_orbit(0),
                                      numpy.ones(len(at_ring)) * 0.6)
    numpy.testing.assert_almost_equal(mocked_ado.get_orbit(1),
                                      numpy.ones(len(at_ring)) * 57)
    numpy.testing.assert_almost_equal(mocked_ado.get_orbit(2),
                                      numpy.ones(len(at_ring)) * 0.2)
    numpy.testing.assert_almost_equal(mocked_ado.get_orbit(3),
                                      numpy.ones(len(at_ring)) * 9)


def test_get_tune(mocked_ado):
    numpy.testing.assert_almost_equal(mocked_ado.get_tune(0), 0.14)
    numpy.testing.assert_almost_equal(mocked_ado.get_tune(1), 0.12)


def test_get_disp(mocked_ado, at_ring):
    numpy.testing.assert_almost_equal(mocked_ado.get_disp(),
                                      (numpy.ones((len(at_ring), 4)) *
                                       numpy.array([8.8, 1.7, 23, 3.5])))


def test_get_s(mocked_ado, at_ring):
    numpy.testing.assert_almost_equal(mocked_ado.get_s(),
                                      numpy.array([0.1 * (i + 1) for i in
                                                   range(len(at_ring))]))


def test_get_energy(mocked_ado):
    assert mocked_ado.get_energy() == 5


def test_get_alpha(mocked_ado, at_ring):
    numpy.testing.assert_almost_equal(mocked_ado.get_alpha(),
                                      (numpy.ones((len(at_ring), 2)) *
                                       numpy.array([-0.03, 0.03])))


def test_get_beta(mocked_ado, at_ring):
    numpy.testing.assert_almost_equal(mocked_ado.get_beta(),
                                      numpy.ones((len(at_ring), 2)) * [9.6, 6])


def test_get_m44(mocked_ado, at_ring):
    numpy.testing.assert_almost_equal(mocked_ado.get_m44(),
                                      (numpy.ones((len(at_ring), 4, 4)) *
                                       numpy.eye(4) * 0.8))


def test_get_mu(mocked_ado, at_ring):
    numpy.testing.assert_almost_equal(mocked_ado.get_mu(),
                                      (numpy.ones((len(at_ring), 2)) *
                                       numpy.array([176, 82])))
