import at
import numpy
import pytac
from warnings import warn
from functools import partial
from threading import Thread, Event
from pytac.data_source import DataSource
from pytac.exceptions import FieldException, HandleException


class ATElementDataSource(DataSource):
    def __init__(self, at_element, accelerator_data, fields=[]):
        self._field_funcs = {'a1': partial(self.PolynomA, 1),
                             'b0': partial(self.PolynomB, 0),
                             'b1': partial(self.PolynomB, 1),
                             'b2': partial(self.PolynomB, 2),
                             'x': partial(self.Orbit, 0),
                             'y': partial(self.Orbit, 2),
                             'x_kick': self.x_kick,
                             'y_kick': self.y_kick,
                             'f': self.Frequency}
        self.units = pytac.PHYS
        self._element = at_element
        self._ad = accelerator_data
        self._fields = fields

    def get_value(self, field, handle=None):
        if field in self._fields:
            return self._field_funcs[field](value=None)
        else:
            raise FieldException("No field {0} on AT element {1}."
                                 .format(field, self._element))

    def set_value(self, field, set_value):
        if field in self._fields:
            self._field_funcs[field](value=set_value)
        else:
            raise FieldException("No field {0} on AT element {1}."
                                 .format(field, self._element))

    def get_fields(self):
        return self._fields

    def PolynomA(self, cell, value):
        # use value as get/set flag as well as the set value.
        if value is None:
            return self._element.PolynomA[cell]
        else:
            self._element.PolynomA[cell] = value
            self._ad.new_changes.set()

    def PolynomB(self, cell, value):
        if value is None:
            return self._element.PolynomB[cell]
        else:
            if isinstance(self._element, at.elements.Quadrupole):
                self._element.K = value
            self._element.PolynomB[cell] = value
            self._ad.new_changes.set()

    def Orbit(self, cell, value):
        index = self._element.Index-1
        if value is None:
            return float(self._ad.get_orbit(cell)[index])
        else:
            field = 'x' if cell is 0 else 'y'
            raise HandleException("Field {0} cannot be set on element data "
                                  "source {1}.".format(field, self))

    def Frequency(self, value):
        if value is None:
            return self._element.Frequency
        else:
            self._element.Frequency = value
            self._ad.new_changes.set()

    def x_kick(self, value):
        if isinstance(self._element, at.elements.Sextupole):
            if value is None:
                return (- self._element.PolynomB[0] * self._element.Length)
            else:
                self._element.PolynomB[0] = (- value / self._element.Length)
                self._ad.new_changes.set()
        else:
            if value is None:
                return self._element.KickAngle[0]
            else:
                self._element.KickAngle[0] = value
                self._ad.new_changes.set()

    def y_kick(self, value):
        if isinstance(self._element, at.elements.Sextupole):
            if value is None:
                return (self._element.PolynomA[0] * self._element.Length)
            else:
                self._element.PolynomA[0] = (value / self._element.Length)
                self._ad.new_changes.set()
        else:
            if value is None:
                return self._element.KickAngle[1]
            else:
                self._element.KickAngle[1] = value
                self._ad.new_changes.set()


class ATLatticeDataSource(DataSource):
    def __init__(self, accelerator_data):
        self.units = pytac.PHYS
        self._ad = accelerator_data
        self._field_funcs = {'chromaticity_x': partial(self._ad.get_chrom, 0),
                             'chromaticity_y': partial(self._ad.get_chrom, 1),
                             'emittance_x': partial(self._ad.get_emit, 0),
                             'emittance_y': partial(self._ad.get_emit, 1),
                             'phase_x': partial(self._ad.get_orbit, 1),
                             'phase_y': partial(self._ad.get_orbit, 3),
                             'tune_x': partial(self._ad.get_tune, 0),
                             'tune_y': partial(self._ad.get_tune, 1),
                             'x': partial(self._ad.get_orbit, 0),
                             'y': partial(self._ad.get_orbit, 2),
                             'dispersion': self._ad.get_disp,
                             'energy': self._ad.get_energy,
                             's_position': self._ad.get_s,
                             'alpha': self._ad.get_alpha,
                             'beta': self._ad.get_beta,
                             'm44': self._ad.get_m44,
                             'mu': self._ad.get_mu}

    def get_value(self, field, handle=None):
        if field in self._field_funcs.keys():
            return self._field_funcs[field]()
        else:
            raise FieldException("Lattice data source {0} does not have field "
                                 "{1}".format(self, field))

    def set_value(self, field):
        raise HandleException("Field {0} cannot be set on lattice data source "
                              "{0}.".format(field, self))

    def get_fields(self):
        return self._field_funcs.keys()


class ATAcceleratorData(object):
    def __init__(self, ring, threads):
        """The phys data must be initially calculated here so that the thread
        has something to reference.
        """
        self._lattice = at.Lattice(ring)
        self._rp = numpy.ones(len(ring), dtype=bool)  # consider using '-'?
        self.new_changes = Event()
        self._paused = Event()
        self._lattice.radiation_on()
        self._emittance = self._lattice.ohmi_envelope(self._rp)
        self._lattice.radiation_off()
        self._lindata = self._lattice.linopt(0, self._rp, True, coupled=False)
        for i in range(threads):
            update = Thread(target=self.calculate_phys_data)
            update.setDaemon(True)
            update.start()

    def calculate_phys_data(self):
        while True:
            if (self.new_changes.is_set() is True) and (self._paused.is_set()
                                                        is False):
                try:
                    self._lattice.radiation_on()
                    self._emittance = self._lattice.ohmi_envelope(self._rp)
                    self._lattice.radiation_off()
                    self._lindata = self._lattice.linopt(0, self._rp, True,
                                                         coupled=False)
                except ValueError as e:
                    warn(at.AtWarning(e))
                self.new_changes.clear()

    def toggle_calculations(self):
        if self._paused.is_set() is False:
            self._paused.set()
        else:
            self._paused.clear()

    def get_element(self, index):
        return self._lattice[index-1]

    def get_ring(self):
        return self._lattice._lattice

    def get_lattice_object(self):
        return self._lattice.copy()

    def get_chrom(self, cell):
        return self._lindata[2][cell]

    def get_emit(self, cell):
        """The emittance of the last element is returned as it should be
        constant throughout the lattice and so cell is returned is arbitrary.
        """
        return self._emittance[2]['emitXY'][:, cell][0]

    def get_orbit(self, cell):
        return self._lindata[3]['closed_orbit'][:, cell]

    def get_tune(self, cell):
        return (self._lindata[1][cell] % 1)

    def get_disp(self):
        return self._lindata[3]['dispersion']

    def get_s(self):
        return self._lindata[3]['s_pos']

    def get_energy(self):
        return self._lattice.energy

    def get_alpha(self):
        return self._lindata[3]['alpha']

    def get_beta(self):
        return self._lindata[3]['beta']

    def get_m44(self):
        return self._lindata[3]['m44']

    def get_mu(self):
        return self._lindata[3]['mu']
