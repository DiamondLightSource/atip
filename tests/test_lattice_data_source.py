from unittest import mock

import pytest
from pytac.exceptions import ControlSystemException, FieldException, HandleException
from testfixtures import LogCapture

import atip


@pytest.mark.parametrize(
    "func_str,field",
    [
        ("atlds._atsim.get_chromaticity", "chromaticity_x"),
        ("atlds._atsim.get_chromaticity", "chromaticity_y"),
        ("atlds._atsim.get_chromaticity", "chromaticity"),
        ("atlds._atsim.get_dispersion", "eta_prime_x"),
        ("atlds._atsim.get_dispersion", "eta_prime_y"),
        ("atlds._atsim.get_dispersion", "dispersion"),
        ("atlds._atsim.get_emittance", "emittance_x"),
        ("atlds._atsim.get_emittance", "emittance_y"),
        ("atlds._atsim.get_emittance", "emittance"),
        ("atlds._atsim.get_orbit", "closed_orbit"),
        ("atlds._atsim.get_dispersion", "eta_x"),
        ("atlds._atsim.get_dispersion", "eta_y"),
        ("atlds._atsim.get_energy", "energy"),
        ("atlds._atsim.get_orbit", "phase_x"),
        ("atlds._atsim.get_orbit", "phase_y"),
        ("atlds._atsim.get_s", "s_position"),
        ("atlds._atsim.get_tune", "tune_x"),
        ("atlds._atsim.get_tune", "tune_y"),
        ("atlds._atsim.get_alpha", "alpha"),
        ("atlds._atsim.get_beta", "beta"),
        ("atlds._atsim.get_tune", "tune"),
        ("atlds._atsim.get_m66", "m66"),
        ("atlds._atsim.get_orbit", "x"),
        ("atlds._atsim.get_orbit", "y"),
        ("atlds._atsim.get_mu", "mu"),
    ],
)
def test_lat_field_funcs(func_str, field, atlds):
    assert atlds._field_funcs[field] == eval(func_str)


def test_lat_get_fields(atlds):
    correct_fields = [
        "chromaticity_x",
        "chromaticity_y",
        "chromaticity",
        "eta_prime_x",
        "eta_prime_y",
        "dispersion",
        "emittance_x",
        "emittance_y",
        "emittance",
        "closed_orbit",
        "eta_x",
        "eta_y",
        "energy",
        "phase_x",
        "phase_y",
        "s_position",
        "tune_x",
        "tune_y",
        "alpha",
        "beta",
        "tune",
        "m66",
        "x",
        "y",
        "mu",
    ]
    fields = atlds.get_fields()
    assert isinstance(fields, list)
    assert len(fields) == len(correct_fields)
    for field in fields:
        assert field in correct_fields


@pytest.mark.parametrize("field", ["not_a_field", 1, [], "BETA", ["x", "y"]])
def test_lat_get_value_raises_FieldException_if_nonexistent_field(atlds, field):
    with pytest.raises(FieldException):
        atlds.get_value(field)


def test_lat_get_value_handles_calculation_check_time_out_correctly():
    atsim = mock.Mock()
    atsim.get_dispersion.return_value = 2.5
    atlds = atip.sim_data_sources.ATLatticeDataSource(atsim)
    atsim.wait_for_calculations.return_value = False
    # Check fails, throw is True, so exception is raised.
    with pytest.raises(ControlSystemException):
        atlds.get_value("dispersion", throw=True)
    # Check fails, throw is False, so warning is logged and value is returned.
    with LogCapture() as log:
        assert atlds.get_value("dispersion", throw=False) == 2.5
    log.check(
        (
            "root",
            "WARNING",
            "Potentially out of date data returned. "
            "Check for completion of outstanding calculations timed out.",
        )
    )
    atsim.wait_for_calculations.return_value = True
    # Check doesn't fail, so doesn't raise error or warn and data is returned.
    assert atlds.get_value("dispersion", throw=True) == 2.5
    assert atlds.get_value("dispersion", throw=False) == 2.5


def test_lat_get_value():
    """We don't need to test every value for get_value() as _field_funcs which
    it relys on has alreadly been tested for all fields."""
    atsim = mock.Mock()
    atsim.get_dispersion.return_value = 2.5
    atlds = atip.sim_data_sources.ATLatticeDataSource(atsim)
    assert atlds.get_value("dispersion") == 2.5
    atlds.get_value("x")
    atsim.get_orbit.assert_called_with("x")
    atlds.get_value("phase_x")
    atsim.get_orbit.assert_called_with("px")
    atlds.get_value("y")
    atsim.get_orbit.assert_called_with("y")
    atlds.get_value("phase_y")
    atsim.get_orbit.assert_called_with("py")


@pytest.mark.parametrize(
    "field", ["not_a_field", 1, [], "BETA", ["x", "y"], "chromaticity_x", "dispersion"]
)
def test_lat_set_value_always_raises_HandleException(atlds, field):
    with pytest.raises(HandleException):
        atlds.set_value(field, 0)
