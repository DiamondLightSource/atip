import mock
import atip
import pytac
import pytest
import numpy


@pytest.mark.parametrize('func_str,field,cell',
                         [('atsim.get_chrom', 'chromaticity_x', 0),
                          ('atsim.get_chrom', 'chromaticity_y', 1),
                          ('atsim.get_emit', 'emittance_x', 0),
                          ('atsim.get_emit', 'emittance_y', 1),
                          ('atsim.get_orbit', 'phase_x', 1),
                          ('atsim.get_orbit', 'phase_y', 3),
                          ('atsim.get_tune', 'tune_x', 0),
                          ('atsim.get_tune', 'tune_y', 1),
                          ('atsim.get_orbit', 'x', 0),
                          ('atsim.get_orbit', 'y', 2),
                          ('atsim.get_disp', 'dispersion', None),
                          ('atsim.get_energy', 'energy', None),
                          ('atsim.get_s', 's_position', None),
                          ('atsim.get_alpha', 'alpha', None),
                          ('atsim.get_beta', 'beta', None),
                          ('atsim.get_m44', 'm44', None),
                          ('atsim.get_mu', 'mu', None)])
def test_lat_field_funcs(func_str, field, cell):
    atsim = mock.Mock()
    atlds = atip.sim_data_sources.ATLatticeDataSource(atsim)
    ff = atlds._field_funcs
    if cell is not None:
        assert ff[field].func == eval(func_str)
        assert ff[field].args[0] == cell
    else:
        assert ff[field] == eval(func_str)


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
    def c(cell):
        return [2.0, 2.5][cell]
    atsim = mock.Mock()
    atsim.get_disp.return_value = numpy.array([[8.8, 1.7, 3.5],
                                               [7.8, 1, -1.4]])
    atsim.get_chrom.return_value = c(0)
    atlds = atip.sim_data_sources.ATLatticeDataSource(atsim)
    assert atlds.get_value('chromaticity_x') == 2.0
    assert atsim.get_chrom.called_with(0)
    numpy.testing.assert_equal(atlds.get_value('dispersion'),
                               numpy.array([[8.8, 1.7, 3.5], [7.8, 1, -1.4]]))


@pytest.mark.parametrize('field', ['not_a_field', 1, [], 'BETA', ['x', 'y'],
                                   'chromaticity_x', 'dispersion'])
def test_lat_set_value_always_raises_HandleException(atlds, field):
    with pytest.raises(pytac.exceptions.HandleException):
        atlds.set_value(field, 0)
