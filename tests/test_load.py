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


@pytest.mark.parametrize("at_and_pytac_lattices", RINGMODES_TO_TEST, indirect=True)
def test_load_pytac_side(at_and_pytac_lattices):
    lat = atip.load_sim.load(at_and_pytac_lattices[0], at_and_pytac_lattices[1])
    # Check lattice has simulator data source
    assert pytac.SIM in lat._data_source_manager._data_sources
    # Check all elements have simulator data source
    for elem in lat:
        assert pytac.SIM in elem._data_source_manager._data_sources
    # Check new lattice fields have a unit conversion
    assert "mu" in lat._data_source_manager._uc
    assert isinstance(lat._data_source_manager._uc["mu"], pytac.units.NullUnitConv)


@pytest.mark.parametrize(
    ["pytac_lattice", "lattice_filepath"],
    [(mode, mode) for mode in RINGMODES_TO_TEST],
    indirect=True,
)
def test_load_atip_and_pytac_lattices(pytac_lattice, lattice_filepath):
    atip.load_sim.load_from_filepath(pytac_lattice, lattice_filepath)


@pytest.mark.parametrize("at_and_pytac_lattices", RINGMODES_TO_TEST, indirect=True)
def test_load_with_non_callable_callback_raises_TypeError(at_and_pytac_lattices):
    with pytest.raises(TypeError):
        atip.load_sim.load(
            at_and_pytac_lattices[0], at_and_pytac_lattices[1], callback=""
        )


@pytest.mark.parametrize("at_and_pytac_lattices", RINGMODES_TO_TEST, indirect=True)
def test_load_with_callback(at_and_pytac_lattices):
    callback_func = mock.Mock()
    lat = atip.load_sim.load(
        at_and_pytac_lattices[0], at_and_pytac_lattices[1], callback=callback_func
    )
    atsim = lat._data_source_manager._data_sources[pytac.SIM]._atsim
    atip.utils.trigger_calc(at_and_pytac_lattices[0])
    atsim.wait_for_calculations()
    callback_func.assert_called_once_with()


def test_load_raises_ValueError_if_incompatible_lattices():
    with pytest.raises(ValueError):
        atip.load_sim.load([1], [1, 2])  # length mismatch


@mock.patch("atip.simulator.calculate_optics")
def test_load_with_default_sim_params(
    mocked_calc_optics,
    pytac_lattice,
    lattice_filepath,
):
    pytac_lattice = atip.load_sim.load_from_filepath(pytac_lattice, lattice_filepath)

    mocked_calc_optics.assert_called_with(
        mock.ANY,
        mock.ANY,
        "linopt6",
        False,
        False,
        False,
    )


@pytest.mark.parametrize(
    "linopt, disable_emittance, disable_chromaticity, disable_radiation",
    [
        ("linopt6", False, True, False),
        ("linopt6", True, True, False),
        ("linopt4", True, False, True),
        ("linopt4", True, True, True),
        ("linopt2", True, False, True),
        ("linopt2", True, True, True),
    ],
)
@mock.patch("atip.simulator.calculate_optics")
def test_load_with_non_default_sim_params(
    mocked_calc_optics,
    pytac_lattice,
    lattice_filepath,
    linopt,
    disable_emittance,
    disable_chromaticity,
    disable_radiation,
):
    pytac_lattice = atip.load_sim.load_from_filepath(
        pytac_lattice,
        lattice_filepath,
        linopt,
        disable_emittance,
        disable_chromaticity,
        disable_radiation,
    )

    mocked_calc_optics.assert_called_with(
        mock.ANY,
        mock.ANY,
        linopt,
        disable_emittance,
        disable_chromaticity,
        disable_radiation,
    )
