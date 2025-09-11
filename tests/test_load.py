from unittest import mock

import pytac
import pytest

import atip

RINGMODES_TO_TEST = ["I04", "DIAD", "48"]


@pytest.mark.parametrize(
    "at_lattice",
    RINGMODES_TO_TEST,
    indirect=True,
)
def test_load_atip_lattice(request, at_lattice):
    assert at_lattice.name == request.node.callspec.params["at_lattice"]


@pytest.mark.parametrize("load_at_and_pytac_lattices", RINGMODES_TO_TEST, indirect=True)
def test_load_pytac_side(load_at_and_pytac_lattices):
    lat = atip.load_sim.load(
        load_at_and_pytac_lattices[0], load_at_and_pytac_lattices[1]
    )
    # Check lattice has simulator data source
    assert pytac.SIM in lat._data_source_manager._data_sources
    # Check all elements have simulator data source
    for elem in lat:
        assert pytac.SIM in elem._data_source_manager._data_sources
    # Check new lattice fields have a unit conversion
    assert "mu" in lat._data_source_manager._uc
    assert isinstance(lat._data_source_manager._uc["mu"], pytac.units.NullUnitConv)


@pytest.mark.parametrize(
    ["pytac_lattice", "get_lattice_filepath"],
    [(mode, mode) for mode in RINGMODES_TO_TEST],
    indirect=True,
)
def test_load_atip_and_pytac_lattices(pytac_lattice, get_lattice_filepath):
    atip.load_sim.load_from_filepath(pytac_lattice, get_lattice_filepath)


@pytest.mark.parametrize("load_at_and_pytac_lattices", RINGMODES_TO_TEST, indirect=True)
def test_load_with_non_callable_callback_raises_TypeError(load_at_and_pytac_lattices):
    with pytest.raises(TypeError):
        atip.load_sim.load(
            load_at_and_pytac_lattices[0], load_at_and_pytac_lattices[1], ""
        )


@pytest.mark.parametrize("load_at_and_pytac_lattices", RINGMODES_TO_TEST, indirect=True)
def test_load_with_callback(load_at_and_pytac_lattices):
    callback_func = mock.Mock()
    lat = atip.load_sim.load(
        load_at_and_pytac_lattices[0], load_at_and_pytac_lattices[1], callback_func
    )
    atsim = lat._data_source_manager._data_sources[pytac.SIM]._atsim
    atip.utils.trigger_calc(load_at_and_pytac_lattices[0])
    atsim.wait_for_calculations()
    callback_func.assert_called_once_with()


def test_load_raises_ValueError_if_incompatible_lattices():
    with pytest.raises(ValueError):
        atip.load_sim.load([1], [1, 2])  # length mismatch
