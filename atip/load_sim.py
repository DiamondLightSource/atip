import pytac
from at import load_mat
from SimulatorModel import ATElementModel, ATLatticeModel

def load(lattice, LATTICE_FILE=None):
    if LATTICE_FILE is None:
        LATTICE_FILE = './vmx.mat'
    ring = load_mat.load(LATTICE_FILE)
    at_interface = ATLatticeModel(ring)
    for x in range(len(ring)):
        ring[x].Index = x+1
        ring[x].Class = ring[x].__doc__.split()[1] #This ensures all elems have a class but likely will not work for other .mat files
    for e in lattice:
        e.set_model(ATElementModel(ring[e.index-1], at_interface, e.get_fields()), pytac.SIM)
    return lattice
