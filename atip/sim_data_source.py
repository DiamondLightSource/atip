import pytac
from at import physics
from threading import Thread
from functools import partial
from pytac.data_source import DataSource
from pytac.exceptions import FieldException, HandleException
try:
    from Queue import Queue  # with a python version < 3.0
except ModuleNotFoundError:  # python 3 support
    from queue import Queue  # with a python version >= 3.0


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
            return self.field_functions[field](value=None)
        else:
            raise FieldException("No field {0} on AT element {1}."
                                 .format(field, self._element))

    def set_value(self, field, set_value):
        if field in self._fields:
            self.field_functions[field](value=set_value)
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
            self.ad.push_changes(self._element)

    def PolynomB(self, cell, value):
        if value is None:
            return self._element.PolynomB[cell]
        else:
            if self._element.Class.lower() == 'quadrupole':
                self._element.K = value
            self._element.PolynomB[cell] = value
            self.ad.push_changes(self._element)

    def Orbit(self, cell, value):
        index = self._element.Index-1
        if value is None:
            return float(self.ad.get_twiss()[0]['closed_orbit'][index][cell])
        else:
            raise HandleException("Must read beam position using {0}."
                                  .format(pytac.RB))

    def Frequency(self, value):
        if value is None:
            return self._element.Frequency
        else:
            self._element.Frequency = value
            self.ad.push_changes(self._element)

    def x_kick(self, value):
        if self._element.Class.lower() == 'sextupole':
            if value is None:
                return (- self._element.PolynomB[0] * self._element.Length)
            else:
                self._element.PolynomB[0] = (- value / self._element.Length)
                self.ad.push_changes(self._element)
        else:
            if value is None:
                return self._element.KickAngle[0]
            else:
                self._element.KickAngle[0] = value
                self.ad.push_changes(self._element)

    def y_kick(self, value):
        if self._element.Class.lower() == 'sextupole':
            if value is None:
                return (self._element.PolynomA[0] * self._element.Length)
            else:
                self._element.PolynomA[0] = (value / self._element.Length)
                self.ad.push_changes(self._element)
        else:
            if value is None:
                return self._element.KickAngle[1]
            else:
                self._element.KickAngle[1] = value
                self.ad.push_changes(self._element)


class ATLatticeDataSource(DataSource):
    def __init__(self, accelerator_data):
        self.units = pytac.PHYS
        self.ad = accelerator_data
        self.field2twiss = {'x': partial(self.read_closed_orbit, field=0),
                            'phase_x': partial(self.read_closed_orbit, field=1),
                            'y': partial(self.read_closed_orbit, field=2),
                            'phase_y': partial(self.read_closed_orbit, field=3),
                            'm44': partial(self.read_twiss0, field='m44'),
                            's_position': partial(self.read_twiss0, field='s_pos'),
                            'alpha': partial(self.read_twiss0, field='alpha'),
                            'beta': partial(self.read_twiss0, field='beta'),
                            'mu': partial(self.read_twiss0, field='mu'),
                            'dispersion': partial(self.read_twiss0, field='dispersion'),
                            'tune_x': partial(self.read_tune, field=0),
                            'tune_y': partial(self.read_tune, field=1),
                            'chromaticity_x': partial(self.read_chrom, field=0),
                            'chromaticity_y': partial(self.read_chrom, field=1),
                            'energy': self.get_energy}

    def get_value(self, field, handle=None):
        if field in self.field2twiss.keys():
            return self.field2twiss[field]()
        else:
            raise FieldException("Lattice data source {0} does not have field "
                                 "{1}".format(self, field))

    def set_value(self, field):
        raise HandleException("Field {0} cannot be set on lattice data source "
                              "{0}.".format(field, self))

    def get_fields(self):
        return self.field2twiss.keys()

    def read_closed_orbit(self, field):
        return self.ad.get_twiss()[0]['closed_orbit'][field]

    def read_twiss0(self, field):
        return self.ad.get_twiss()[0][field]

    def read_tune(self, field):
        return (self.ad.get_twiss()[1][field] % 1)

    def read_chrom(self, field):
        return self.ad.get_twiss()[2][field]

    def get_energy(self, magnitude):
        return int(self.ad.get_ring()[0].Energy)


class ATAcceleratorData(object):
    def __init__(self, ring, threads):
        self.q = Queue()
        self.ring = ring
        self.thread_number = threads
        self.twiss = physics.get_twiss(self.ring, get_chrom=True)
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
                self.twiss = physics.get_twiss(self.ring, get_chrom=True)
            self.q.task_done()

    def get_twiss(self):
        return self.twiss

    def get_element(self, index):
        self.q.join()
        return self.ring[index-1]

    def get_ring(self):
        self.q.join()
        return self.ring
