import mock
import pytac
import pytest

import atip


@pytest.mark.parametrize('func_str,field', [
    ('atlds._atsim.get_orbit', 'phase_y'), ('atlds._atsim.get_alpha', 'alpha'),
    ('atlds._atsim.get_emit', 'emittance_x'), ('atlds._atsim.get_orbit', 'x'),
    ('atlds._atsim.get_emit', 'emittance_y'), ('atlds._atsim.get_orbit', 'y'),
    ('atlds._atsim.get_tune', 'tune_x'), ('atlds._atsim.get_tune', 'tune_y'),
    ('atlds._atsim.get_orbit', 'phase_x'), ('atlds._atsim.get_beta', 'beta'),
    ('atlds._atsim.get_disp', 'dispersion'), ('atlds._atsim.get_mu', 'mu'),
    ('atlds._atsim.get_energy', 'energy'), ('atlds._atsim.get_m44', 'm44'),
    ('atlds._atsim.get_chrom', 'chromaticity_x'),
    ('atlds._atsim.get_chrom', 'chromaticity_y'),
    ('atlds._atsim.get_s', 's_position')
])
def test_lat_field_funcs(func_str, field, atlds):
    assert atlds._field_funcs[field] == eval(func_str)


def test_lat_get_fields(atlds):
    correct_fields = ['chromaticity_x', 'chromaticity_y', 'emittance_x',
                      'emittance_y', 'phase_x', 'phase_y', 'tune_x', 'tune_y',
                      'x', 'y', 'dispersion', 'energy', 's_position', 'alpha',
                      'beta', 'm44', 'mu']
    fields = atlds.get_fields()
    assert isinstance(fields, list)
    assert len(fields) == len(correct_fields)
    for field in fields:
        assert field in correct_fields


@pytest.mark.parametrize('field', ['not_a_field', 1, [], 'BETA', ['x', 'y']])
def test_lat_get_value_raises_FieldException_if_nonexistent_field(atlds,
                                                                  field):
    with pytest.raises(pytac.exceptions.FieldException):
        atlds.get_value(field)


def test_lat_get_value():
    """We don't need to test every value for get_value() as _field_funcs which
    it relys on has alreadly been tested for all fields."""
    atsim = mock.Mock()
    atsim.get_disp.return_value = 2.5
    atlds = atip.sim_data_sources.ATLatticeDataSource(atsim)
    assert atlds.get_value('dispersion') == 2.5
    atlds.get_value('x')
    assert atsim.get_orbit.called_with('x')
    atlds.get_value('phase_x')
    assert atsim.get_orbit.called_with('px')
    atlds.get_value('y')
    assert atsim.get_orbit.called_with('y')
    atlds.get_value('phase_y')
    assert atsim.get_orbit.called_with('py')


@pytest.mark.parametrize('field', ['not_a_field', 1, [], 'BETA', ['x', 'y'],
                                   'chromaticity_x', 'dispersion'])
def test_lat_set_value_always_raises_HandleException(atlds, field):
    with pytest.raises(pytac.exceptions.HandleException):
        atlds.set_value(field, 0)
