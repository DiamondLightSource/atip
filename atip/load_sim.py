import pytac
from at import load_mat
from SimulatorModel import SimulatorModel

def load(lattice, LATTICE_FILE=None):
    if LATTICE_FILE is None:
        LATTICE_FILE = './vmx.mat'
    AT = at_interface(LATTICE_FILE)
    ring = load_mat.load(LATTICE_FILE)
    for x in range(len(ring)):
        ring[x].Index = x+1
        ring[x].Class = ring[x].__doc__.split()[1] #This ensures all elems have a class but likely will not work for other .mat files
    for e in lattice:
        e.set_model(SimulatorModel(ring[e.index-1], AT), pytac.SIM) #could be combined with the above loop - is the clarity of separation worth the extra loop
    return lattice

class at_interface(object):
    def __init__(self, LATTICE_FILE):
        self.ring = load_mat.load(LATTICE_FILE)
    def push_changes(self, element):
        self.ring[element.Index-1] = element
    def pull_ring(self):
        return self.ring
