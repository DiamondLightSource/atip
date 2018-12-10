import atip
import at
import pytest
import numpy


def initial_phys_data(ado, initial_emit, initial_lin):
    try:
        numpy.testing.assert_almost_equal(initial_emit[2]['emitXY'][:, 0][0],
                                          ado.get_emit(0), decimal=15)
        numpy.testing.assert_almost_equal(initial_emit[2]['emitXY'][:, 1][0],
                                          ado.get_emit(1), decimal=15)
        numpy.testing.assert_almost_equal(initial_lin[1][0], ado.get_tune(0),
                                          decimal=8)
        numpy.testing.assert_almost_equal(initial_lin[1][1], ado.get_tune(1),
                                          decimal=8)
        numpy.testing.assert_almost_equal(initial_lin[2][0], ado.get_chrom(0),
                                          decimal=8)
        numpy.testing.assert_almost_equal(initial_lin[2][1], ado.get_chrom(1),
                                          decimal=8)
        numpy.testing.assert_almost_equal(initial_lin[3]['closed_orbit'][:, 0],
                                          ado.get_orbit(0))
        numpy.testing.assert_almost_equal(initial_lin[3]['closed_orbit'][:, 1],
                                          ado.get_orbit(1))
        numpy.testing.assert_almost_equal(initial_lin[3]['closed_orbit'][:, 2],
                                          ado.get_orbit(2))
        numpy.testing.assert_almost_equal(initial_lin[3]['closed_orbit'][:, 3],
                                          ado.get_orbit(3))
        numpy.testing.assert_almost_equal(initial_lin[3]['dispersion'][-1],
                                          ado.get_disp()[-1], decimal=11)
        numpy.testing.assert_almost_equal(initial_lin[3]['s_pos'], ado.get_s(),
                                          decimal=8)
        numpy.testing.assert_almost_equal(initial_lin[3]['alpha'][-1],
                                          ado.get_alpha()[-1], decimal=14)
        numpy.testing.assert_almost_equal(initial_lin[3]['beta'][-1],
                                          ado.get_beta()[-1], decimal=8)
        numpy.testing.assert_almost_equal(initial_lin[3]['m44'][-1],
                                          ado.get_m44()[-1], decimal=8)
        numpy.testing.assert_almost_equal(initial_lin[3]['mu'][-1],
                                          ado.get_mu()[-1], decimal=8)
        return True
    except Exception:
        return False


def test_accelerator_data_object_creation(at_ring, initial_emit, initial_lin):
    ado = atip.sim_data_source.ATAcceleratorData(at_ring)
    # Check initial state of flags.
    assert ado.up_to_date.is_set() is True
    assert ado._paused.is_set() is False
    assert ado._running.is_set() is False
    # Check emittance and lindata are initially calculated correctly.
    assert initial_phys_data(ado, initial_emit, initial_lin) is True


def test_start_and_stop_thread(at_ring):
    ado = atip.sim_data_source.ATAcceleratorData(at_ring)
    assert ado._running.is_set() is False
    assert ado._calculation_thread.is_alive() is False
    with pytest.raises(RuntimeError):
        ado.stop_thread()
    ado.start_thread()
    with pytest.raises(RuntimeError):
        ado.start_thread()
    assert ado._running.is_set() is True
    assert ado._calculation_thread.is_alive() is True
    ado.stop_thread()
    assert ado._running.is_set() is False
    assert ado._calculation_thread.is_alive() is False


def test_recalculate_phys_data(at_ring, initial_emit, initial_lin):
    ado = atip.sim_data_source.ATAcceleratorData(at_ring)
    assert initial_phys_data(ado, initial_emit, initial_lin) is True
    ado.start_thread()
    # Check that errors raised inside thread are converted to warnings.
    ado._lattice[6].PolynomB[0] = 1.e10
    with pytest.warns(at.AtWarning):
        ado.up_to_date.clear()
        ado.wait_for_calculations(5)
    ado._lattice[6].PolynomB[0] = 0.0
    # Set corrector x_kick but on a sextupole as no correctors in the test ring
    ado._lattice[22].PolynomB[0] = -7.e-5
    # Set corrector y_kick but on a sextupole as no correctors in the test ring
    ado._lattice[22].PolynomA[0] = 7.e-5
    # Set quadrupole b1
    ado._lattice[6].PolynomB[1] = 2.5
    # Set skew quadrupole a1
    ado._lattice[8].PolynomA[1] = 2.25e-3
    # Set sextupole b2
    ado._lattice[22].PolynomB[2] = -75
    # Clear the flag and then wait for the calculations
    ado.up_to_date.clear()
    ado.wait_for_calculations(5)
    # Get the applicable physics data
    orbit = [ado.get_orbit(0)[0], ado.get_orbit(2)[0]]
    chrom = [ado.get_chrom(0), ado.get_chrom(1)]
    tune = [ado.get_tune(0), ado.get_tune(1)]
    emit = [ado.get_emit(0), ado.get_emit(1)]
    ado.stop_thread()
    # Check the results against known values
    numpy.testing.assert_almost_equal(orbit, [5.18918914e-06, -8.92596857e-06],
                                      decimal=10)
    numpy.testing.assert_almost_equal(chrom, [0.11732846, 0.04300947],
                                      decimal=8)
    numpy.testing.assert_almost_equal(tune, [0.37444833, 0.86048592],
                                      decimal=8)
    numpy.testing.assert_almost_equal(emit, [1.34308653e-10, 3.74339964e-13],
                                      decimal=15)


def test_toggle_calculations_and_wait_for_calculations(at_ring, initial_emit,
                                                       initial_lin):
    ado = atip.sim_data_source.ATAcceleratorData(at_ring)
    assert ado._paused.is_set() is False
    ado.toggle_calculations()
    assert ado._paused.is_set() is True
    ado.toggle_calculations()
    assert ado._paused.is_set() is False
    ado.start_thread()
    # pause > make a change > check no calc > unpause > check calc
    ado.toggle_calculations()
    ado._lattice[6].PolynomB[1] = 2.5
    ado.up_to_date.clear()
    assert ado.wait_for_calculations(5) is False
    assert initial_phys_data(ado, initial_emit, initial_lin) is True
    ado.toggle_calculations()
    assert ado.wait_for_calculations(10) is True
    assert initial_phys_data(ado, initial_emit, initial_lin) is False
    ado.stop_thread()


def test_get_element(at_ring):
    ado = atip.sim_data_source.ATAcceleratorData(at_ring)
    assert ado.get_element(1) == at_ring[0]


def test_get_ring(at_ring):
    ado = atip.sim_data_source.ATAcceleratorData(at_ring)
    assert ado.get_ring() == at_ring


def test_get_lattice_object(at_ring):
    ado = atip.sim_data_source.ATAcceleratorData(at_ring)
    assert ado.get_lattice_object() == ado._lattice


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
