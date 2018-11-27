import at
import numpy
import pytac
from threading import Thread
from functools import partial
from pytac.data_source import DataSource
from pytac.exceptions import FieldException, HandleException


class ATElementDataSource(DataSource):
    def __init__(self, at_element, accelerator_data, fields=[]):
        self._field_func = {'a1': partial(self.PolynomA, cell=1),
                            'b0': partial(self.PolynomB, cell=0),
                            'b1': partial(self.PolynomB, cell=1),
                            'b2': partial(self.PolynomB, cell=2),
                            'x': partial(self.Orbit, cell=0),
                            'y': partial(self.Orbit, cell=2),
                            'x_kick': self.x_kick,
                            'y_kick': self.y_kick,
                            'f': self.Frequency}
        self.units = pytac.PHYS
        self._element = at_element
        self._ad = accelerator_data
        self._fields = fields

    def get_value(self, field, handle=None):
        if field in self._fields:
            return self._field_func[field](value=None)
        else:
            raise FieldException("No field {0} on AT element {1}."
                                 .format(field, self._element))

    def set_value(self, field, set_value):
        if field in self._fields:
            self._field_func[field](value=set_value)
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
            self._ad.new_changes = True

    def PolynomB(self, cell, value):
        if value is None:
            return self._element.PolynomB[cell]
        else:
            if isinstance(self._element, at.elements.Quadrupole):
                self._element.K = value
            self._element.PolynomB[cell] = value
            self._ad.new_changes = True

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
            self._ad.new_changes = True

    def x_kick(self, value):
        if isinstance(self._element, at.elements.Sextupole):
            if value is None:
                return (- self._element.PolynomB[0] * self._element.Length)
            else:
                self._element.PolynomB[0] = (- value / self._element.Length)
                self._ad.new_changes = True
        else:
            if value is None:
                return self._element.KickAngle[0]
            else:
                self._element.KickAngle[0] = value
                self._ad.new_changes = True

    def y_kick(self, value):
        if isinstance(self._element, at.elements.Sextupole):
            if value is None:
                return (self._element.PolynomA[0] * self._element.Length)
            else:
                self._element.PolynomA[0] = (value / self._element.Length)
                self._ad.new_changes = True
        else:
            if value is None:
                return self._element.KickAngle[1]
            else:
                self._element.KickAngle[1] = value
                self._ad.new_changes = True


class ATLatticeDataSource(DataSource):
    def __init__(self, accelerator_data):
        self.units = pytac.PHYS
        self._ad = accelerator_data
        self._field_func = {'chromaticity_x': partial(self._ad.get_chrom, cell=0),
                            'chromaticity_y': partial(self._ad.get_chrom, cell=1),
                            'emittance_x': partial(self._ad.get_emit, cell=0),
                            'emittance_y': partial(self._ad.get_emit, cell=1),
                            'phase_x': partial(self._ad.get_orbit, cell=1),
                            'phase_y': partial(self._ad.get_orbit, cell=3),
                            'tune_x': partial(self._ad.get_tune, cell=0),
                            'tune_y': partial(self._ad.get_tune, cell=1),
                            'x': partial(self._ad.get_orbit, cell=0),
                            'y': partial(self._ad.get_orbit, cell=2),
                            'dispersion': self._ad.get_dispersion,
                            's_position': self._ad.get_spos,
                            'energy': self._ad.get_energy,
                            'alpha': self._ad.get_alpha,
                            'beta': self._ad.get_beta,
                            'm44': self._ad.get_m44,
                            'mu': self._ad.get_mu}

    def get_value(self, field, handle=None):
        if field in self._field_func.keys():
            return self._field_func[field]()
        else:
            raise FieldException("Lattice data source {0} does not have field "
                                 "{1}".format(self, field))

    def set_value(self, field):
        raise HandleException("Field {0} cannot be set on lattice data source "
                              "{0}.".format(field, self))

    def get_fields(self):
        return self._field_func.keys()


class ATAcceleratorData(object):
    def __init__(self, ring, threads):
        """new_changes is initially False so that phys data is not needlessly 
        recalculated immediately by the threads.
        """
        self._lattice_object = at.Lattice(ring)
        self._rp = numpy.ones(len(ring), dtype=bool)  # consider using new string syntax?
        self.new_changes = False
        self._lattice_object.radiation_on()
        self._emittance = self._lattice_object.ohmi_envelope(self._rp)
        self._lattice_object.radiation_off()
        self._lindata = self._lattice_object.linopt(refpts=self._rp,
                                                    get_chrom=True,
                                                    coupled=False)
        for i in range(threads):
            update = Thread(target=self.calculate_phys_data)
            update.setDaemon(True)
            update.start()

    def calculate_phys_data(self):
        while True:
            if self.new_changes is True:
                self._lattice_object.radiation_on()
                self._emittance = self._lattice_object.ohmi_envelope(self._rp)
                self._lattice_object.radiation_off()
                self._lindata = self._lattice_object.linopt(refpts=self._rp,
                                                            get_chrom=True,
                                                            coupled=False)
                self.new_changes = False

    def get_element(self, index):
        return self._lattice_object[index-1]

    def get_ring(self):
        return self._lattice_object._lattice

    def get_lattice_object(self):
        return self._lattice_object

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

    def get_dispersion(self):
        return self._lindata[3]['dispersion']

    def get_spos(self):
        return self._lindata[3]['s_pos']

    def get_energy(self):
        return self._lattice_object.energy

    def get_alpha(self):
        return self._lindata[3]['alpha']

    def get_beta(self):
        return self._lindata[3]['beta']

    def get_m44(self):
        return self._lindata[3]['m44']

    def get_mu(self):
        return self._lindata[3]['mu']
