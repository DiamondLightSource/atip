import at
import mock
import numpy
import pytest
from scipy.constants import speed_of_light
from pytac.exceptions import FieldException

import atip


def _check_initial_phys_data(atsim, initial_phys_data):
    try:
        numpy.testing.assert_almost_equal(initial_phys_data['emitXY'][0],
                                          atsim.get_emittance('x'), decimal=6)
        numpy.testing.assert_almost_equal(initial_phys_data['emitXY'][1],
                                          atsim.get_emittance('y'), decimal=14)
        numpy.testing.assert_almost_equal(initial_phys_data['tune'][0],
                                          atsim.get_tune('x'), decimal=6)
        numpy.testing.assert_almost_equal(initial_phys_data['tune'][1],
                                          atsim.get_tune('y'), decimal=8)
        numpy.testing.assert_almost_equal(initial_phys_data['chromaticity'][0],
                                          atsim.get_chromaticity('x'),
                                          decimal=8)
        numpy.testing.assert_almost_equal(initial_phys_data['chromaticity'][1],
                                          atsim.get_chromaticity('y'),
                                          decimal=8)
        numpy.testing.assert_almost_equal(initial_phys_data['closed_orbit'][0],
                                          atsim.get_orbit('x'))
        numpy.testing.assert_almost_equal(initial_phys_data['closed_orbit'][1],
                                          atsim.get_orbit('px'))
        numpy.testing.assert_almost_equal(initial_phys_data['closed_orbit'][2],
                                          atsim.get_orbit('y'))
        numpy.testing.assert_almost_equal(initial_phys_data['closed_orbit'][3],
                                          atsim.get_orbit('py'))
        numpy.testing.assert_almost_equal(initial_phys_data['dispersion'],
                                          atsim.get_dispersion()[-1],
                                          decimal=6)
        numpy.testing.assert_almost_equal(initial_phys_data['s_pos'],
                                          atsim.get_s(), decimal=8)
        numpy.testing.assert_almost_equal(initial_phys_data['alpha'],
                                          atsim.get_alpha()[-1], decimal=8)
        numpy.testing.assert_almost_equal(initial_phys_data['beta'],
                                          atsim.get_beta()[-1], decimal=8)
        numpy.testing.assert_almost_equal(initial_phys_data['m44'],
                                          atsim.get_m44()[-1], decimal=8)
        numpy.testing.assert_almost_equal(initial_phys_data['mu'],
                                          atsim.get_mu()[-1], decimal=8)
        numpy.testing.assert_almost_equal(initial_phys_data['rad_int'],
                                          atsim.get_radiation_integrals(),
                                          decimal=14)
        return True
    except Exception:
        return False


def test_ATSimulator_creation(atsim, initial_phys_data):
    # Check initial state of flags.
    assert bool(atsim._paused) is False
    assert bool(atsim.up_to_date) is True
    assert len(atsim._queue) == 0
    # Check physics data is initially calculated correctly.
    assert _check_initial_phys_data(atsim, initial_phys_data) is True


def test_recalculate_phys_data_queue(atsim):
    elem_ds = mock.Mock()
    atsim.up_to_date.Reset()
    atsim.queue_set(elem_ds._make_change, 'a_field', 12)
    assert len(atsim._queue) == 1
    atsim.wait_for_calculations()
    assert len(atsim._queue) == 0
    elem_ds._make_change.assert_called_once_with('a_field', 12)


def test_recalculate_phys_data(atsim, initial_phys_data):
    assert _check_initial_phys_data(atsim, initial_phys_data) is True
    # Check that errors raised inside thread are converted to warnings.
    atsim._at_lat[5].PolynomB[0] = 1.e10
    atsim.up_to_date.Reset()
    atsim.queue_set(mock.Mock(), 'f', 0)
    with pytest.warns(at.AtWarning):
        atsim.wait_for_calculations()
    atsim._at_lat[5].PolynomB[0] = 0.0
    # Set corrector x_kick but on a sextupole as no correctors in test ring
    atsim._at_lat[21].PolynomB[0] = -7.e-5
    # Set corrector y_kick but on a sextupole as no correctors in test ring
    atsim._at_lat[21].PolynomA[0] = 7.e-5
    # Set quadrupole b1
    atsim._at_lat[5].PolynomB[1] = 2.5
    # Set skew quadrupole a1
    atsim._at_lat[7].PolynomA[1] = 2.25e-3
    # Set sextupole b2
    atsim._at_lat[21].PolynomB[2] = -75
    # Clear the flag and then wait for the calculations
    atsim.up_to_date.Reset()
    atsim.queue_set(mock.Mock(), 'f', 0)
    atsim.wait_for_calculations()
    # Get the applicable physics data
    orbit = [atsim.get_orbit('x')[0], atsim.get_orbit('y')[0]]
    chrom = [atsim.get_chromaticity('x'), atsim.get_chromaticity('y')]
    tune = [atsim.get_tune('x'), atsim.get_tune('y')]
    emit = [atsim.get_emittance('x'), atsim.get_emittance('y')]
    # Check the results against known values
    numpy.testing.assert_almost_equal(orbit, [5.18918914e-06, -8.92596857e-06],
                                      decimal=10)
    numpy.testing.assert_almost_equal(chrom, [0.11732846, 0.04300947],
                                      decimal=5)
    numpy.testing.assert_almost_equal(tune, [0.37444833, 0.86048592],
                                      decimal=8)
    numpy.testing.assert_almost_equal(emit, [1.34308653e-10, 3.74339964e-13],
                                      decimal=15)


def test_toggle_calculations_and_wait_for_calculations(atsim,
                                                       initial_phys_data):
    assert bool(atsim._paused) is False
    atsim.toggle_calculations()
    assert bool(atsim._paused) is True
    atsim.toggle_calculations()
    assert bool(atsim._paused) is False
    # pause > make a change > check no calc > unpause > check calc
    atsim.toggle_calculations()
    atsim._at_lat[5].PolynomB[1] = 2.5
    atsim.up_to_date.Reset()
    atsim.queue_set(mock.Mock(), 'f', 0)
    assert atsim.wait_for_calculations(2) is False
    assert _check_initial_phys_data(atsim, initial_phys_data) is True
    atsim.toggle_calculations()
    atsim.queue_set(mock.Mock(), 'f', 0)
    assert atsim.wait_for_calculations() is True
    assert _check_initial_phys_data(atsim, initial_phys_data) is False


def test_recalculate_phys_data_callback(at_lattice):
    # Check ATSimulator is created successfully if no callback.
    atip.simulator.ATSimulator(at_lattice)
    # Check non-callable callback argument raises TypeError.
    with pytest.raises(TypeError):
        atip.simulator.ATSimulator(at_lattice, '')
    callback_func = mock.Mock()
    atsim = atip.simulator.ATSimulator(at_lattice, callback_func)
    atsim.up_to_date.Reset()
    atsim.queue_set(mock.Mock(), 'f', 0)
    atsim.wait_for_calculations()
    callback_func.assert_called_once_with()


def test_get_at_element(atsim, at_lattice):
    assert atsim.get_at_element(1) == at_lattice[0]


def test_get_at_lattice(atsim, at_lattice):
    for elem1, elem2 in zip(atsim.get_at_lattice(), atsim._at_lat):
        assert elem1 == elem2


def test_get_s(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(mocked_atsim.get_s(),
                                      numpy.array([0.1 * (i + 1) for i in
                                                   range(len(at_lattice))]))


def test_get_total_bend_angle(ba_atsim):
    assert ba_atsim.get_total_bend_angle() == numpy.degrees(0.5)


def test_get_total_absolute_bend_angle(ba_atsim):
    assert ba_atsim.get_total_absolute_bend_angle() == numpy.degrees(2.1)


def test_get_energy(mocked_atsim):
    assert mocked_atsim.get_energy() == 5


def test_get_tune(mocked_atsim):
    numpy.testing.assert_almost_equal(mocked_atsim.get_tune(), [0.14, 0.12])
    numpy.testing.assert_almost_equal(mocked_atsim.get_tune('x'), 0.14)
    numpy.testing.assert_almost_equal(mocked_atsim.get_tune('y'), 0.12)
    with pytest.raises(FieldException):
        mocked_atsim.get_tune('not_a_field')


def test_get_chromaticity(mocked_atsim):
    numpy.testing.assert_equal(mocked_atsim.get_chromaticity(), [2, 1])
    assert mocked_atsim.get_chromaticity('x') == 2
    assert mocked_atsim.get_chromaticity('y') == 1
    with pytest.raises(FieldException):
        mocked_atsim.get_chromaticity('not_a_field')


def test_get_orbit(mocked_atsim, at_lattice):
    all_orbit = numpy.ones((len(at_lattice), 4)) * numpy.array([[0.6, 57,
                                                                 0.2, 9]])
    numpy.testing.assert_almost_equal(mocked_atsim.get_orbit(), all_orbit)
    numpy.testing.assert_almost_equal(mocked_atsim.get_orbit('x'),
                                      all_orbit[:, 0])
    numpy.testing.assert_almost_equal(mocked_atsim.get_orbit('px'),
                                      all_orbit[:, 1])
    numpy.testing.assert_almost_equal(mocked_atsim.get_orbit('y'),
                                      all_orbit[:, 2])
    numpy.testing.assert_almost_equal(mocked_atsim.get_orbit('py'),
                                      all_orbit[:, 3])
    with pytest.raises(FieldException):
        mocked_atsim.get_orbit('not_a_field')


def test_get_dispersion(mocked_atsim, at_lattice):
    all_eta = numpy.ones((len(at_lattice), 4)) * numpy.array([[8.8, 1.7,
                                                               23, 3.5]])
    numpy.testing.assert_almost_equal(mocked_atsim.get_dispersion(), all_eta)
    numpy.testing.assert_almost_equal(mocked_atsim.get_dispersion('x'),
                                      all_eta[:, 0])
    numpy.testing.assert_almost_equal(mocked_atsim.get_dispersion('px'),
                                      all_eta[:, 1])
    numpy.testing.assert_almost_equal(mocked_atsim.get_dispersion('y'),
                                      all_eta[:, 2])
    numpy.testing.assert_almost_equal(mocked_atsim.get_dispersion('py'),
                                      all_eta[:, 3])
    with pytest.raises(FieldException):
        mocked_atsim.get_dispersion('not_a_field')


def test_get_alpha(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        mocked_atsim.get_alpha(),
        (numpy.ones((len(at_lattice), 2)) * numpy.array([-0.03, 0.03]))
    )


def test_get_beta(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        mocked_atsim.get_beta(),
        (numpy.ones((len(at_lattice), 2)) * numpy.array([9.6, 6]))
    )


def test_get_mu(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        mocked_atsim.get_mu(),
        (numpy.ones((len(at_lattice), 2)) * numpy.array([176, 82]))
    )


def test_get_m44(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        mocked_atsim.get_m44(),
        (numpy.ones((len(at_lattice), 4, 4)) * numpy.eye(4) * 0.8)
    )


def test_get_emittance(mocked_atsim):
    numpy.testing.assert_equal(mocked_atsim.get_emittance(), [1.4, 0.45])
    assert mocked_atsim.get_emittance('x') == 1.4
    assert mocked_atsim.get_emittance('y') == 0.45
    with pytest.raises(FieldException):
        mocked_atsim.get_emittance('not_a_field')


def test_get_radiation_integrals(mocked_atsim):
    numpy.testing.assert_equal(numpy.array([1, 2, 3, 4, 5]),
                               mocked_atsim.get_radiation_integrals())


def test_get_momentum_compaction(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(0.08196721311475409,
                                      mocked_atsim.get_momentum_compaction())


def test_get_energy_spread(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(3.709154355564931e-12,
                                      mocked_atsim.get_energy_spread())


def test_get_energy_loss(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(1.7599102965879e-29,
                                      mocked_atsim.get_energy_loss())


def test_get_damping_partition_numbers(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        numpy.array([-1, 1, 4]),
        mocked_atsim.get_damping_partition_numbers()
    )


def test_get_damping_times(mocked_atsim, at_lattice):
    E0 = 5
    U0 = mocked_atsim.get_energy_loss()
    T0 = 0.1 * (len(at_lattice) + 1) / speed_of_light
    damping_partition_numbers = mocked_atsim.get_damping_partition_numbers()
    damping_times = (2 * T0 * E0) / (U0 * damping_partition_numbers)
    numpy.testing.assert_almost_equal(damping_times,
                                      mocked_atsim.get_damping_times())


def test_get_linear_dispersion_action(mocked_atsim):
    assert mocked_atsim.get_linear_dispersion_action() == 2.5


def test_get_horizontal_emittance(mocked_atsim):
    eps_x = -(62.5 * at.physics.Cq) / at.physics.e_mass**2
    assert mocked_atsim.get_horizontal_emittance() == eps_x
