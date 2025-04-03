from unittest import mock

import pytac
import pytest

import atip


def test_load_pytac_side(pytac_lattice, at_diad_lattice):
    lat = atip.load_sim.load(pytac_lattice, at_diad_lattice)
    # Check lattice has simulator data source
    assert pytac.SIM in lat._data_source_manager._data_sources
    # Check all elements have simulator data source
    for elem in lat:
        assert pytac.SIM in elem._data_source_manager._data_sources
    # Check new lattice fields have a unit conversion
    assert "mu" in lat._data_source_manager._uc
    assert isinstance(lat._data_source_manager._uc["mu"], pytac.units.NullUnitConv)


def test_load_from_filepath(pytac_lattice, mat_filepath):
    atip.load_sim.load_from_filepath(pytac_lattice, mat_filepath)


def test_load_with_non_callable_callback_raises_TypeError(
    pytac_lattice, at_diad_lattice
):
    with pytest.raises(TypeError):
        atip.load_sim.load(pytac_lattice, at_diad_lattice, "")


def test_load_with_callback(pytac_lattice, at_diad_lattice):
    callback_func = mock.Mock()
    lat = atip.load_sim.load(pytac_lattice, at_diad_lattice, callback_func)
    atsim = lat._data_source_manager._data_sources[pytac.SIM]._atsim
    atip.utils.trigger_calc(pytac_lattice)
    atsim.wait_for_calculations()
    callback_func.assert_called_once_with()


def test_load_raises_ValueError_if_incompatible_lattices():
    with pytest.raises(ValueError):
        atip.load_sim.load([1], [1, 2])  # length mismatch
