from functools import partial
import numpy
import pytac
from at import physics
from pytac.exceptions import FieldException, HandleException


class ATElementDataSource(object):
    def __init__(self, at_element, at_interface, fields=[]):
        self.field_functions = {'a0' : partial(self.PolynomA, cell=0),
                                'a1' : partial(self.PolynomA, cell=1),
                                'b0' : partial(self.PolynomB, cell=0),
                                'b1' : partial(self.PolynomB, cell=1),
                                'b2' : partial(self.PolynomB, cell=2),
                                'x' : partial(self.Orbit, field='x'),
                                'y' : partial(self.Orbit, field='y'),
                                'f' : self.Frequency}
        self.units = pytac.PHYS #conversion is done in element.(set/get)_value before and after pass
        self.at = at_interface
        self._element = at_element
        self._fields = fields
    
    def get_value(self, field, handle):
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
    
    def PolynomA(self, cell, value): #use value as get/set flag as well as the set value
        if numpy.isnan(value):
            return self._element.PolynomA[cell]
        else:
            self._element.PolynomA[cell] = value
            self.at.push_changes(self._element)
    
    def PolynomB(self, cell, value):
        if numpy.isnan(value):
            return self._element.PolynomB[cell]
        else:
            self._element.PolynomB[cell] = value
            self.at.push_changes(self._element)
    
    def Orbit(self, field, value):
        index = self._element.Index-1
        if numpy.isnan(value):
            return float(self.at.get_value(field)[index])
        else:
            raise HandleException("Must read beam position using {}".format(pytac.RB))
    
    def Frequency(self, value):
        if numpy.isnan(value):
            return self._element.Frequency
        else:
            self._element.Frequency = value
            self.at.push_changes(self._element)


class ATLatticeDataSource(object):
    def __init__(self, ring):
        self.ring = ring
        #temporary work around for AT None bug:
        self.rp = []
        for x in range(len(self.ring)):
            self.rp.append(x)
        #work around end
        self.twiss = physics.get_twiss(self.ring, refpts=self.rp, get_chrom=True)
        self.field2twiss = {'x' : partial(self.read_twiss, cell=0, field='closed_orbit', limiter=0),
                            'px' : partial(self.read_twiss, cell=0, field='closed_orbit', limiter=1),
                            'y' : partial(self.read_twiss, cell=0, field='closed_orbit', limiter=2),
                            'py' : partial(self.read_twiss, cell=0, field='closed_orbit', limiter=3),
                            'm44' : partial(self.read_twiss, cell=0, field='m44', limiter=None),
                            'idx' : partial(self.read_twiss, cell=0, field='idx', limiter=None),
                            's_pos' : partial(self.read_twiss, cell=0, field='s_pos', limiter=None),
                            'alpha' : partial(self.read_twiss, cell=0, field='alpha', limiter=None),
                            'beta' : partial(self.read_twiss, cell=0, field='beta', limiter=None),
                            'mu' : partial(self.read_twiss, cell=0, field='mu', limiter=None),
                            'dispersion' : partial(self.read_twiss, cell=0, field='dispersion', limiter=None),
                            'tune' : partial(self.read_twiss, cell=1, field=None, limiter=None),
                            'chrom' : partial(self.read_twiss, cell=2, field=None, limiter=None)}

    def get_value(self, field):
        if field in self.field2twiss.keys():
            self.twiss = physics.get_twiss(self.ring, refpts=self.rp, get_chrom=True)
            return self.field2twiss[field]()
        else:
            raise FieldException('Lattice data_source {} does not have field {}'.format(self, field))
    
    def set_value(self, field):
        raise HandleException('Filed {} cannot be set on lattice data_source {}'.format(field, self))
    
    def get_fields(self):
        return self.field2twiss.keys()
    
    def read_twiss(self, cell, field, limiter):
        if field==None:
            return self.twiss[cell]
        elif limiter==None:
            return self.twiss[cell][field]
        else:
            return self.twiss[cell][field][:,limiter]
    
    def push_changes(self, element):
        self.ring[element.Index-1] = element
