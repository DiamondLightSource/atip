from functools import partial
import numpy
import pytac
from at import physics

class ATModel(object):
    def __init__(self, at_element, at_interface, fields):
        self.field_functions = {'a0' : partial(self.PolynomA, cell=0),
                                'a1' : partial(self.PolynomA, cell=1),
                                'b0' : partial(self.PolynomB, cell=0),
                                'b1' : partial(self.PolynomB, cell=1),
                                'b2' : partial(self.PolynomB, cell=2),
                                'x' : partial(self.Orbit, cell=0),
                                'y' : partial(self.Orbit, cell=2),
                                'f' : self.Frequency}
        self.units = pytac.PHYS #conversion is done in element.(set/get)_value before and after pass
        self._element = at_element
        self.at = at_interface
        self.fields = list(fields)
    
    def get_value(self, field, handle):
        return self.field_functions[field](value=numpy.nan)
    
    def set_value(self, field, set_value):
        self.field_functions[field](value=set_value)
    
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
    
    def Orbit(self, cell, value):
        index = self._element.Index-1
        if numpy.isnan(value):
            return float(physics.find_orbit4(self.at.pull_ring(), refpts=index)[1][cell])
        else:
            raise ThisIsReadbackOnlyError
    
    def Frequency(self, value):
        if numpy.isnan(value):
            return self._element.Frequency
        else:
            self._element.Frequency = value
            self.at.push_changes(self._element)
    
    def get_fields(self):
        return self.fields
