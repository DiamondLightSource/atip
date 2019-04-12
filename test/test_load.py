import at
import mock
import pytac
import pytest
import atip


def test_load_pytac_side(pytac_lattice, at_ring):
    lat = atip.load_sim.load(pytac_lattice, at.lattice.Lattice(at_ring))
    # Check lattice has simulator data source
    assert pytac.SIM in lat._data_source_manager._data_sources
    # Check all elements have simulator data source
    for elem in lat:
        assert pytac.SIM in elem._data_source_manager._data_sources
    # Check new lattice fields have a unit conversion
    assert 'mu' in lat._data_source_manager._uc
    assert lat._data_source_manager._uc['mu'] is pytac.load_csv.DEFAULT_UC


def test_load_at_ring_variations(pytac_lattice, mat_filepath, at_ring):
    # Check at lattice loads from lattice object
    lat = atip.load_sim.load(pytac_lattice, at.lattice.Lattice(at_ring))
    # Check at lattice loads from filepath
    lat = atip.load_sim.load(pytac_lattice, mat_filepath)
    # Check at lattice loads from ring
    lat = atip.load_sim.load(pytac_lattice, at_ring)


def test_load_with_callback(pytac_lattice, at_ring):
    # Check normal load
    lat = atip.load_sim.load(pytac_lattice, at_ring)
    # Check load with non-callable raises TypeError
    with pytest.raises(TypeError):
        atip.load_sim.load(pytac_lattice, at_ring, '')
    # Check load with callable
    callback_func = mock.Mock()
    lat = atip.load_sim.load(pytac_lattice, at_ring, callback_func)
    atsim = lat._data_source_manager._data_sources[pytac.SIM]._atsim
    atip.ease.trigger_calc(pytac_lattice)
    atsim.wait_for_calculations()
    callback_func.assert_called_once_with()
