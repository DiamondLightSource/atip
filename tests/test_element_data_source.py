from unittest import mock

import at
import pytest
from pytac.exceptions import ControlSystemException, FieldException, HandleException
from testfixtures import LogCapture

import atip


@pytest.mark.parametrize(
    "func_str,field,cell",
    [
        ("ateds._get_KickAngle", "x_kick", 0),
        ("ateds._get_PolynomA", "a1", 1),
        ("ateds._get_KickAngle", "y_kick", 1),
        ("ateds._get_PolynomB", "b1", 1),
        ("ateds._get_BendingAngle", "b0", None),
        ("ateds._get_PolynomB", "b2", 2),
        ("ateds._get_ClosedOrbit", "x", "x"),
        ("ateds._get_Frequency", "f", None),
        ("ateds._get_ClosedOrbit", "y", "y"),
    ],
)
def test_get_elem_field_funcs(at_elem, func_str, field, cell):
    ateds = atip.sim_data_sources.ATElementDataSource(at_elem, 1, mock.Mock(), [field])
    get_ff = ateds._get_field_funcs
    if cell is not None:  # i.e. functools partial is returned.
        assert get_ff[field].func == eval(func_str)
        assert get_ff[field].args[0] == cell
    else:
        assert get_ff[field] == eval(func_str)


@pytest.mark.parametrize(
    "func_str,field,cell",
    [
        ("ateds._set_KickAngle", "x_kick", 0),
        ("ateds._set_PolynomA", "a1", 1),
        ("ateds._set_KickAngle", "y_kick", 1),
        ("ateds._set_PolynomB", "b1", 1),
        ("ateds._set_BendingAngle", "b0", None),
        ("ateds._set_PolynomB", "b2", 2),
        ("ateds._set_Frequency", "f", None),
    ],
)
def test_set_elem_field_funcs(at_elem, func_str, field, cell):
    ateds = atip.sim_data_sources.ATElementDataSource(at_elem, 1, mock.Mock(), [field])
    set_ff = ateds._set_field_funcs
    if cell is not None:  # i.e. functools partial is returned.
        assert set_ff[field].func == eval(func_str)
        assert set_ff[field].args[0] == cell
    else:
        assert set_ff[field] == eval(func_str)


@pytest.mark.parametrize("fields", [["a1", "a1"], ["x_kick", "b0", "x_kick"]])
def test_elem_removes_duplicated_fields(at_elem, fields):
    ateds = atip.sim_data_sources.ATElementDataSource(at_elem, 1, mock.Mock(), fields)
    assert ateds.get_fields() == list(set(fields))


@pytest.mark.parametrize(
    "fields", [["not_a_field"], [1], ["a1", "invalid"], ["X_KICK"]]
)
def test_elem_raises_FieldException_if_unsupported_field(at_elem, fields):
    with pytest.raises(FieldException):
        atip.sim_data_sources.ATElementDataSource(at_elem, 1, mock.Mock(), fields)


@pytest.mark.parametrize("fields", [["a1"], ["x_kick", "y_kick"], []])
def test_elem_get_fields(at_elem, fields):
    ateds = atip.sim_data_sources.ATElementDataSource(at_elem, 1, mock.Mock(), fields)
    assert len(ateds.get_fields()) == len(fields)
    assert set(ateds.get_fields()) == set(fields)


@pytest.mark.parametrize("fields", [["f", "b0"], ["b1", "b2"]])
def test_elem_add_field(at_elem, fields):
    ateds = atip.sim_data_sources.ATElementDataSource(at_elem, 1, mock.Mock())
    assert len(ateds.get_fields()) == 0
    ateds.add_field(fields[0])
    assert len(ateds.get_fields()) == 1
    ateds.add_field(fields[1])
    assert len(ateds.get_fields()) == 2


@pytest.mark.parametrize("field", ["f", "not_a_field"])
def test_elem_add_field_raises_FieldExceptions_correctly(at_elem, field):
    ateds = atip.sim_data_sources.ATElementDataSource(at_elem, 1, mock.Mock(), ["f"])
    with pytest.raises(FieldException):
        ateds.add_field(field)


def test_elem_get_value_handles_calculation_check_time_out_correctly(at_elem):
    atsim = mock.Mock()
    ateds = atip.sim_data_sources.ATElementDataSource(at_elem, 1, atsim, ["f"])
    atsim.wait_for_calculations.return_value = False
    # Check fails, throw is True, so exception is raised.
    with pytest.raises(ControlSystemException):
        ateds.get_value("f", throw=True)
    # Check fails, throw is False, so warning is logged and value is returned.
    with LogCapture() as log:
        assert ateds.get_value("f", throw=False) == 0
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
    assert ateds.get_value("f", throw=True) == 0
    assert ateds.get_value("f", throw=False) == 0


@pytest.mark.parametrize("field", ["not_a_field", 1, [], "a1", "X_KICK"])
def test_elem_get_value_raises_FieldException_if_nonexistent_field(at_elem, field):
    ateds = atip.sim_data_sources.ATElementDataSource(
        at_elem, 1, mock.Mock(), ["x_kick"]
    )
    with pytest.raises(FieldException):
        ateds.get_value(field)


@pytest.mark.parametrize(
    "field,value",
    [
        ("x_kick", 0.1),
        ("y_kick", 0.01),
        ("f", 500),
        ("a1", 13),
        ("b0", 0.13),
        ("b1", -0.07),
        ("b2", 42),
    ],
)
def test_elem_get_value(at_elem_preset, field, value):
    ateds = atip.sim_data_sources.ATElementDataSource(
        at_elem_preset, 6, mock.Mock(), [field]
    )
    assert ateds.get_value(field) == value


def test_elem_get_orbit(at_elem_preset):
    atsim = mock.Mock()
    atsim.get_orbit.return_value = [27, 53, 741, 16, 12, 33]
    ateds = atip.sim_data_sources.ATElementDataSource(
        at_elem_preset, 6, atsim, ["x", "y"]
    )
    assert ateds.get_value("x") == 33
    ateds._index = 3
    assert ateds.get_value("y") == 741


def test_elem_get_value_on_Sextupole():
    s = at.elements.Sextupole(
        "S1", 0.1, PolynomA=[50, 0, 0, 0], PolynomB=[-10, 0, 0, 0]
    )
    ateds = atip.sim_data_sources.ATElementDataSource(
        s, 0, mock.Mock(), ["x_kick", "y_kick"]
    )
    assert ateds.get_value("x_kick") == 1
    assert ateds.get_value("y_kick") == 5


@pytest.mark.parametrize("field", ["not_a_field", 1, [], "a1", "X_KICK"])
def test_elem_set_value_raises_FieldException_if_nonexistant_field(at_elem, field):
    ateds = atip.sim_data_sources.ATElementDataSource(
        at_elem, 1, mock.Mock(), ["x_kick"]
    )
    with pytest.raises(FieldException):
        ateds.set_value(field, 0)


@pytest.mark.parametrize("field", ["x", "y"])
def test_elem_set_orbit_raises_HandleException(at_elem, field):
    ateds = atip.sim_data_sources.ATElementDataSource(at_elem, 1, mock.Mock(), [field])
    with pytest.raises(HandleException):
        ateds.set_value(field, 0)


@pytest.mark.parametrize("field", ["x_kick", "y_kick", "a1", "b0", "b1", "b2", "f"])
def test_elem_set_value_adds_changes_to_queue(at_elem, field):
    atsim = mock.Mock()
    ateds = atip.sim_data_sources.ATElementDataSource(at_elem, 1, atsim, [field])
    ateds.set_value(field, 1)
    assert len(atsim.queue_set.mock_calls) == 1
    assert atsim.queue_set.mock_calls[0] == mock.call(ateds._make_change, field, 1)


@pytest.mark.parametrize(
    "field,attr_str",
    [
        ("x_kick", "at_elem.KickAngle[0]"),
        ("y_kick", "at_elem.KickAngle[1]"),
        ("a1", "at_elem.PolynomA[1]"),
        ("b0", "at_elem.BendingAngle"),
        ("b1", "at_elem.PolynomB[1]"),
        ("b2", "at_elem.PolynomB[2]"),
        ("f", "at_elem.Frequency"),
    ],
)
def test_elem_make_change(at_elem, field, attr_str):
    ateds = atip.sim_data_sources.ATElementDataSource(at_elem, 1, mock.Mock(), [field])
    ateds._make_change(field, 1)
    assert eval(attr_str) == 1


def test_elem_make_change_on_Sextupole():
    s = at.elements.Sextupole("S1", 0.1, PolynomA=[0, 0, 0, 0], PolynomB=[0, 0, 0, 0])
    ateds = atip.sim_data_sources.ATElementDataSource(
        s, 0, mock.Mock(), ["x_kick", "y_kick"]
    )
    ateds._make_change("x_kick", 1)
    ateds._make_change("y_kick", 5)
    assert s.PolynomA[0] == (5 / 0.1)
    assert s.PolynomB[0] == (-1 / 0.1)
