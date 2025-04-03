from unittest import mock

import at
import cothread
import numpy
import pytest
from pytac.exceptions import DataSourceException, FieldException
from scipy.constants import speed_of_light

import atip


def _check_initial_phys_data(atsim, initial_phys_data):
    numpy.testing.assert_almost_equal(
        initial_phys_data["emitXY"][0], atsim.get_emittance("x"), decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["emitXY"][1], atsim.get_emittance("y"), decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["tune"][0], atsim.get_tune("x"), decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["tune"][1], atsim.get_tune("y"), decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["chromaticity"][0], atsim.get_chromaticity("x"), decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["chromaticity"][1], atsim.get_chromaticity("y"), decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["closed_orbit"][0], atsim.get_orbit("x"), decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["closed_orbit"][1], atsim.get_orbit("px"), decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["closed_orbit"][2], atsim.get_orbit("y"), decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["closed_orbit"][3], atsim.get_orbit("py"), decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["dispersion"], atsim.get_dispersion()[-1], decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["s_pos"], atsim.get_s(), decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["alpha"], atsim.get_alpha()[-1], decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["beta"], atsim.get_beta()[-1], decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["m66"], atsim.get_m66()[-1], decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["mu"], atsim.get_mu()[-1], decimal=3
    )
    numpy.testing.assert_almost_equal(
        initial_phys_data["rad_int"], atsim.get_radiation_integrals(), decimal=3
    )


def test_ATSimulator_creation(atsim, initial_phys_data):
    # Check initial state of flags.
    assert not atsim._paused
    assert atsim.up_to_date
    assert len(atsim._queue) == 0
    # Check physics data is initially calculated correctly.
    _check_initial_phys_data(atsim, initial_phys_data)


def test_recalculate_phys_data_queue(atsim):
    elem_ds = mock.Mock()
    assert atsim.up_to_date
    atsim.queue_set(elem_ds._make_change, "a_field", 12)
    assert not atsim.up_to_date
    cothread.Sleep(0.1)
    elem_ds._make_change.assert_called_once_with("a_field", 12)


def test_pause_calculations(atsim):
    elem_ds = mock.Mock()
    atsim.pause_calculations()
    atsim.queue_set(elem_ds._make_change, "a_field", 12)
    cothread.Sleep(0.1)
    # Queue emptied even though paused.
    assert len(atsim._queue) == 0
    elem_ds._make_change.assert_called_once_with("a_field", 12)
    # Calculation not updated because paused.
    assert not atsim.up_to_date
    # Check we don't have to add another item to the queue to prompt a recalculation.
    atsim.unpause_calculations()
    cothread.Sleep(0.1)
    # Calculation now updated.
    assert atsim.up_to_date


def test_quit_calculation_thread(atsim):
    # Check our thread initially works
    atsim._lattice_data = None
    atsim.trigger_calculation()
    assert atsim.wait_for_calculations() is True
    assert len(atsim._queue) == 0
    assert atsim._lattice_data is not None
    # Stop the calculation thread
    assert len(atsim._queue) == 0
    atsim.quit_calculation_thread()
    assert len(atsim._queue) == 0
    # Check our thread no longer works
    atsim._lattice_data = None
    atsim.trigger_calculation()
    assert atsim.wait_for_calculations(2) is False
    assert len(atsim._queue) == 1
    assert atsim._lattice_data is None


def test_gather_one_sample(atsim):
    # Stop the calculation thread from emptying the queue
    atsim.quit_calculation_thread()
    # Add something to the queue
    elem_ds = mock.Mock()
    atsim.queue_set(elem_ds._make_change, "a_field", 12)
    cothread.Sleep(0.1)
    # Make sure it's on the queue and hasn't already been gathered
    assert len(atsim._queue) == 1
    elem_ds._make_change.assert_not_called()
    # Gather it off the queue and check that our mock change has been called correctly
    atsim._gather_one_sample()
    assert len(atsim._queue) == 0
    elem_ds._make_change.assert_called_once_with("a_field", 12)


def test_recalculate_phys_data(atsim, initial_phys_data):
    _check_initial_phys_data(atsim, initial_phys_data)
    # Check that errors raised inside thread are converted to warnings.
    atsim._at_lat[5].PolynomB[0] = 1.0e10
    atsim.queue_set(mock.Mock(), "f", 0)
    with pytest.warns(at.AtWarning):
        atsim.wait_for_calculations()
    atsim._at_lat[5].PolynomB[0] = 0.0
    # Set corrector x_kick but on a sextupole as no correctors in test ring
    atsim._at_lat[21].PolynomB[0] = -7.0e-5
    # Set corrector y_kick but on a sextupole as no correctors in test ring
    atsim._at_lat[21].PolynomA[0] = 7.0e-5
    # Set quadrupole b1
    atsim._at_lat[5].PolynomB[1] = 2.5
    # Set skew quadrupole a1
    atsim._at_lat[7].PolynomA[1] = 2.25e-3
    # Set sextupole b2
    atsim._at_lat[21].PolynomB[2] = -75
    # Clear the flag and then wait for the calculations
    atsim.queue_set(mock.Mock(), "f", 0)
    atsim.wait_for_calculations()
    # Get the applicable physics data
    orbit = [atsim.get_orbit("x")[0], atsim.get_orbit("y")[0]]
    chrom = [atsim.get_chromaticity("x"), atsim.get_chromaticity("y")]
    tune = [atsim.get_tune("x"), atsim.get_tune("y")]
    emit = [atsim.get_emittance("x"), atsim.get_emittance("y")]
    # Check the results against known values
    numpy.testing.assert_almost_equal(
        orbit, [5.18918914e-06, -8.92596857e-06], decimal=3
    )
    numpy.testing.assert_almost_equal(chrom, [0.11732846, 0.04300947], decimal=2)
    numpy.testing.assert_almost_equal(tune, [0.37444833, 0.86048592], decimal=3)
    numpy.testing.assert_almost_equal(emit, [1.34308653e-10, 3.74339964e-13], decimal=3)


def test_disable_emittance_flag(atsim, initial_phys_data):
    # Check emittance data is intially there
    assert not atsim._disable_emittance
    assert len(atsim._lattice_data.emittance) == 3
    # Check that ohmi_envelope is called when disable_emittance is False
    atsim._at_lat.ohmi_envelope = mock.Mock()
    atsim.trigger_calculation()
    cothread.Sleep(0.1)
    atsim._at_lat.ohmi_envelope.assert_called_once()
    # Check that ohmi_envelope isn't called when disable_emittance is True and that
    # there isn't any emittance data
    atsim._disable_emittance = True
    atsim._at_lat.ohmi_envelope.reset_mock()
    atsim.trigger_calculation()
    cothread.Sleep(0.1)
    atsim._at_lat.ohmi_envelope.assert_not_called()
    assert len(atsim._lattice_data.emittance) == 0


def test_toggle_calculations_and_wait_for_calculations(atsim, initial_phys_data):
    assert not atsim._paused
    atsim.toggle_calculations()
    assert atsim._paused
    atsim.toggle_calculations()
    assert not atsim._paused
    # pause > make a change > check no calc > unpause > check calc
    atsim.toggle_calculations()
    atsim._at_lat[5].PolynomB[1] = 2.5
    atsim.queue_set(mock.Mock(), "f", 0)
    assert atsim.wait_for_calculations(2) is False
    _check_initial_phys_data(atsim, initial_phys_data)
    atsim.toggle_calculations()
    atsim.queue_set(mock.Mock(), "f", 0)
    assert atsim.wait_for_calculations() is True
    # Physics data has changed.
    with pytest.raises(AssertionError):
        _check_initial_phys_data(atsim, initial_phys_data)


def test_recalculate_phys_data_callback(at_lattice):
    # Check ATSimulator is created successfully if no callback.
    atip.simulator.ATSimulator(at_lattice)
    # Check non-callable callback argument raises TypeError.
    with pytest.raises(TypeError):
        atip.simulator.ATSimulator(at_lattice, "")
    callback_func = mock.Mock()
    atsim = atip.simulator.ATSimulator(at_lattice, callback_func)
    atsim.queue_set(mock.Mock(), "f", 0)
    atsim.wait_for_calculations()
    callback_func.assert_called_once_with()


def test_get_at_element(atsim, at_lattice):
    assert atsim.get_at_element(1) == at_lattice[0]


def test_get_at_lattice(atsim, at_lattice):
    for elem1, elem2 in zip(atsim.get_at_lattice(), atsim._at_lat, strict=False):
        assert elem1 == elem2


def test_get_s(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        mocked_atsim.get_s(),
        numpy.array([0.1 * (i + 1) for i in range(len(at_lattice))]),
    )


def test_get_total_bend_angle(ba_atsim):
    assert ba_atsim.get_total_bend_angle() == numpy.degrees(0.5)


def test_get_total_absolute_bend_angle(ba_atsim):
    assert ba_atsim.get_total_absolute_bend_angle() == numpy.degrees(2.1)


def test_get_energy(mocked_atsim):
    assert mocked_atsim.get_energy() == 5


def test_get_tune(mocked_atsim):
    numpy.testing.assert_almost_equal(mocked_atsim.get_tune(), [0.14, 0.12])
    numpy.testing.assert_almost_equal(mocked_atsim.get_tune("x"), 0.14)
    numpy.testing.assert_almost_equal(mocked_atsim.get_tune("y"), 0.12)
    with pytest.raises(FieldException):
        mocked_atsim.get_tune("not_a_field")


def test_get_chromaticity(mocked_atsim):
    numpy.testing.assert_equal(mocked_atsim.get_chromaticity(), [2, 1])
    assert mocked_atsim.get_chromaticity("x") == 2
    assert mocked_atsim.get_chromaticity("y") == 1
    with pytest.raises(FieldException):
        mocked_atsim.get_chromaticity("not_a_field")


def test_get_orbit(mocked_atsim, at_lattice):
    all_orbit = numpy.ones((len(at_lattice), 4)) * numpy.array([[0.6, 57, 0.2, 9]])
    numpy.testing.assert_almost_equal(mocked_atsim.get_orbit(), all_orbit)
    numpy.testing.assert_almost_equal(mocked_atsim.get_orbit("x"), all_orbit[:, 0])
    numpy.testing.assert_almost_equal(mocked_atsim.get_orbit("px"), all_orbit[:, 1])
    numpy.testing.assert_almost_equal(mocked_atsim.get_orbit("y"), all_orbit[:, 2])
    numpy.testing.assert_almost_equal(mocked_atsim.get_orbit("py"), all_orbit[:, 3])
    with pytest.raises(FieldException):
        mocked_atsim.get_orbit("not_a_field")


def test_get_dispersion(mocked_atsim, at_lattice):
    all_eta = numpy.ones((len(at_lattice), 4)) * numpy.array([[8.8, 1.7, 23, 3.5]])
    numpy.testing.assert_almost_equal(mocked_atsim.get_dispersion(), all_eta)
    numpy.testing.assert_almost_equal(mocked_atsim.get_dispersion("x"), all_eta[:, 0])
    numpy.testing.assert_almost_equal(mocked_atsim.get_dispersion("px"), all_eta[:, 1])
    numpy.testing.assert_almost_equal(mocked_atsim.get_dispersion("y"), all_eta[:, 2])
    numpy.testing.assert_almost_equal(mocked_atsim.get_dispersion("py"), all_eta[:, 3])
    with pytest.raises(FieldException):
        mocked_atsim.get_dispersion("not_a_field")


def test_get_alpha(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        mocked_atsim.get_alpha(),
        (numpy.ones((len(at_lattice), 2)) * numpy.array([-0.03, 0.03])),
    )


def test_get_beta(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        mocked_atsim.get_beta(),
        (numpy.ones((len(at_lattice), 2)) * numpy.array([9.6, 6])),
    )


def test_get_mu(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        mocked_atsim.get_mu(),
        (numpy.ones((len(at_lattice), 2)) * numpy.array([176, 82])),
    )


def test_get_m66(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        mocked_atsim.get_m66(),
        (numpy.ones((len(at_lattice), 6, 6)) * numpy.eye(6) * 0.8),
    )


def test_get_emittance(mocked_atsim):
    assert not mocked_atsim._disable_emittance
    numpy.testing.assert_equal(mocked_atsim.get_emittance(), [1.4, 0.45])
    assert mocked_atsim.get_emittance("x") == 1.4
    assert mocked_atsim.get_emittance("y") == 0.45
    with pytest.raises(FieldException):
        mocked_atsim.get_emittance("not_a_field")
    mocked_atsim._disable_emittance = True
    with pytest.raises(DataSourceException):
        mocked_atsim.get_emittance()


def test_get_radiation_integrals(mocked_atsim):
    numpy.testing.assert_equal(
        numpy.array([1, 2, 3, 4, 5]), mocked_atsim.get_radiation_integrals()
    )


def test_get_momentum_compaction(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        0.08196721311475409, mocked_atsim.get_momentum_compaction()
    )


def test_get_energy_spread(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        3.709154355564931e-12, mocked_atsim.get_energy_spread()
    )


def test_get_energy_loss(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        1.7599102965879e-29, mocked_atsim.get_energy_loss()
    )


def test_get_damping_partition_numbers(mocked_atsim, at_lattice):
    numpy.testing.assert_almost_equal(
        numpy.array([-1, 1, 4]), mocked_atsim.get_damping_partition_numbers()
    )


def test_get_damping_times(mocked_atsim, at_lattice):
    E0 = 5
    U0 = mocked_atsim.get_energy_loss()
    T0 = 0.1 * (len(at_lattice) + 1) / speed_of_light
    damping_partition_numbers = mocked_atsim.get_damping_partition_numbers()
    damping_times = (2 * T0 * E0) / (U0 * damping_partition_numbers)
    numpy.testing.assert_almost_equal(damping_times, mocked_atsim.get_damping_times())


def test_get_linear_dispersion_action(mocked_atsim):
    assert mocked_atsim.get_linear_dispersion_action() == 2.5


def test_get_horizontal_emittance(mocked_atsim):
    eps_x = -(62.5 * at.constants.Cq) / at.constants.e_mass**2
    numpy.testing.assert_almost_equal(eps_x, mocked_atsim.get_horizontal_emittance())
