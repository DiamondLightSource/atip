import numpy
import pytac
from at import physics
from threading import Thread
from functools import partial
from pytac.data_source import DataSource
from pytac.exceptions import FieldException, HandleException
try:
    from Queue import Queue
except ModuleNotFoundError:
    from queue import Queue


class ATElementDataSource(DataSource):
    def __init__(self, at_element, accelerator_data, fields=[]):
        self.field_functions = {'a1': partial(self.PolynomA, cell=1),
                                'b0': partial(self.PolynomB, cell=0),
                                'b1': partial(self.PolynomB, cell=1),
                                'b2': partial(self.PolynomB, cell=2),
                                'x': partial(self.Orbit, cell=0),
                                'y': partial(self.Orbit, cell=2),
                                'f': self.Frequency,
                                'x_kick': self.x_kick,
                                'y_kick': self.y_kick}
        self.units = pytac.PHYS
        self._element = at_element
        self.ad = accelerator_data
        self._fields = fields

    def get_value(self, field, handle=None):
        if field in self._fields:
            return self.field_functions[field](value=numpy.nan)
        else:
            raise FieldException("No field {} on AT element {}".format(field, self._element))

    def set_value(self, field, set_value):
        if field in self._fields:
            self.field_functions[field](value=set_value)
        else:
            raise FieldException("No field {} on AT element {}".format(field, self._element))

    def get_fields(self):
        return self._fields

    def PolynomA(self, cell, value):
        # use value as get/set flag as well as the set value.
        if numpy.isnan(value):
            return self._element.PolynomA[cell]
        else:
            self._element.PolynomA[cell] = value
            self.ad.push_changes(self._element)

    def PolynomB(self, cell, value):
        if numpy.isnan(value):
            return self._element.PolynomB[cell]
        else:
            if self._element.Class == 'quadrupole':
                self._element.K = value
            self._element.PolynomB[cell] = value
            self.ad.push_changes(self._element)

    def Orbit(self, cell, value):
        index = self._element.Index-1
        if numpy.isnan(value):
            return float(self.ad.get_twiss()[0]['closed_orbit'][index][cell])
        else:
            raise HandleException("Must read beam position using {}".format(pytac.RB))

    def Frequency(self, value):
        if numpy.isnan(value):
            return self._element.Frequency
        else:
            self._element.Frequency = value
            self.ad.push_changes(self._element)

    def x_kick(self, value):
        if self._element.Class == 'sextupole':
            if numpy.isnan(value):
                return (- self._element.PolynomB[0] * self._element.Length)
            else:
                self._element.PolynomB[0] = (- value / self._element.Length)
                self.ad.push_changes(self._element)
        else:
            if numpy.isnan(value):
                return self._element.KickAngle[0]
            else:
                self._element.KickAngle[0] = value
                self.ad.push_changes(self._element)

    def y_kick(self, value):
        if self._element.Class == 'sextupole':
            if numpy.isnan(value):
                return (self._element.PolynomA[0] * self._element.Length)
            else:
                self._element.PolynomA[0] = (value / self._element.Length)
                self.ad.push_changes(self._element)
        else:
            if numpy.isnan(value):
                return self._element.KickAngle[1]
            else:
                self._element.KickAngle[1] = value
                self.ad.push_changes(self._element)


class ATLatticeDataSource(DataSource):
    def __init__(self, accelerator_data):
        self.units = pytac.PHYS
        self.ad = accelerator_data
        # temporary work around for AT None bug:
        self.rp = []
        for x in range(len(self.ad.get_ring())):
            self.rp.append(x)
        # work around end.
        self.field2twiss = {'x': partial(self.read_twiss, cell=0, field='closed_orbit', limiter=0),
                            'phase_x': partial(self.read_twiss, cell=0, field='closed_orbit', limiter=1),
                            'y': partial(self.read_twiss, cell=0, field='closed_orbit', limiter=2),
                            'phase_y': partial(self.read_twiss, cell=0, field='closed_orbit', limiter=3),
                            'm44': partial(self.read_twiss, cell=0, field='m44', limiter=None),
                            's_position': partial(self.read_twiss, cell=0, field='s_pos', limiter=None),
                            'alpha': partial(self.read_twiss, cell=0, field='alpha', limiter=None),
                            'beta': partial(self.read_twiss, cell=0, field='beta', limiter=None),
                            'mu': partial(self.read_twiss, cell=0, field='mu', limiter=None),
                            'dispersion': partial(self.read_twiss, cell=0, field='dispersion', limiter=None),
                            'tune_x': partial(self.read_twiss, cell=1, field=0, limiter='fractional digits'),
                            'tune_y': partial(self.read_twiss, cell=1, field=1, limiter='fractional digits'),
                            'chromaticity_x': partial(self.read_twiss, cell=2, field=0, limiter=None),
                            'chromaticity_y': partial(self.read_twiss, cell=2, field=1, limiter=None),
                            'energy': partial(self.get_energy, magnitude=1.e+06)}

    def get_value(self, field, handle=None):
        if field in self.field2twiss.keys():
            return self.field2twiss[field]()
        else:
            raise FieldException('Lattice data_source {} does not have field {}'.format(self, field))

    def set_value(self, field):
        raise HandleException('Field {} cannot be set on lattice data_source {}'.format(field, self))

    def get_fields(self):
        return self.field2twiss.keys()

    def read_twiss(self, cell, field, limiter):
        twiss = self.ad.get_twiss()
        if (field is None) and (limiter is None):
            return twiss[cell]
        elif limiter is None:
            return twiss[cell][field]
        elif field is None:
            if limiter == 'fractional digits':
                return twiss[cell] % 1
            else:
                return twiss[cell][:, limiter]
        else:
            if limiter == 'fractional digits':
                return twiss[cell][field] % 1
            else:
                return twiss[cell][field][:, limiter]

    def get_energy(self, magnitude):
        return int(self.ad.get_ring()[0].Energy[0] / magnitude)


class ATAcceleratorData(object):
    def __init__(self, ring, threads):
        self.q = Queue()
        self.ring = ring
        self.thread_number = threads
        # temporary work around for AT None bug:
        self.rp = []
        for x in range(len(self.ring)):
            self.rp.append(x)
        # work around end.
        self.twiss = physics.get_twiss(self.ring, refpts=self.rp, get_chrom=True)
        for i in range(self.thread_number):
            update = Thread(target=self.update_ring)
            update.setDaemon(True)
            update.start()

    def push_changes(self, *elements):
        for element in elements:
            self.q.put(element)

    def update_ring(self):
        while True:
            element = self.q.get()
            self.ring[element.Index-1] = element
            if self.q.empty():
                self.twiss = physics.get_twiss(self.ring, refpts=self.rp, get_chrom=True)
            self.q.task_done()

    def get_twiss(self):
        return self.twiss

    def get_element(self, index):
        self.q.join()
        return self.ring[index-1]

    def get_ring(self):
        self.q.join()
        return self.ring
