import numpy
import pytac
from at import load_mat
from pytac.load_csv import UNIT_UC
from sim_data_source import *
"""
UNSIMULATED_FIELDS = ['db0', 'enabled', 'x_fofb_disabled', 'x_sofb_disabled',
                      'y_fofb_disabled', 'y_sofb_disabled', 'h_fofb_disabled',
                      'h_sofb_disabled', 'v_fofb_disabled', 'v_sofb_disabled']
"""


SIMULATED_FIELDS = ['a1', 'b0', 'b1', 'b2', 'x', 'y', 'f', 'x_kick', 'y_kick']


def load(lattice, LATTICE_FILE=None):
    if LATTICE_FILE is None:
        LATTICE_FILE = './vmx.mat'
    ring = load_mat.load(LATTICE_FILE)
    ring = fix_dtype(ring)
    ad = ATAcceleratorData(ring, 1)
    lattice.set_data_source(ATLatticeDataSource(ad), pytac.SIM)
    at_interface = lattice._data_source_manager._data_sources[pytac.SIM]
    for x in range(len(ring)):
        ring[x].Index = x+1
# This ensures all elems have a class but will not work for other lattice files
        ring[x].Class = ring[x].__doc__.split()[1]
    for e in lattice:
        sim_fields = []
        live_fields = list(e.get_fields()[pytac.LIVE])
        for x in range(len(live_fields)):
            if live_fields[x] in SIMULATED_FIELDS:
                sim_fields.append(live_fields[x])
        e.set_data_source(ATElementDataSource(ring[e.index-1], ad, sim_fields),
                          pytac.SIM)
    for f in lattice.get_fields()[pytac.SIM]:
        if f not in lattice._data_source_manager._uc.keys():
            lattice._data_source_manager._uc[f] = UNIT_UC
    return lattice


def fix_dtype(ring):
    for element in ring:
        attributes = element.__dict__.keys()
        for attribute in attributes:
            if isinstance(vars(element)[attribute], numpy.ndarray):
                try:
                    vars(element)[attribute] = numpy.float64(vars(element)[attribute])
                    vars(element)[attribute] = numpy.asfortranarray(vars(element)[attribute])
                except ValueError:
                    vars(element)[attribute].dtype = '<f8'
    return ring
