import pytac
from at import load_mat
from pytac.load_csv import DEFAULT_UC
from sim_data_source import ATElementDataSource, ATLatticeDataSource, ATAcceleratorData


SIMULATED_FIELDS = ['a1', 'b0', 'b1', 'b2', 'x', 'y', 'f', 'x_kick', 'y_kick']


def load(lattice, LATTICE_FILE):
    ring = load_mat.load(LATTICE_FILE)
    for x in range(len(ring)):
        if not hasattr(ring[x], 'Index'):
            ring[x].Index = x + 1
        # Fix becasue APs are using old version of AT.
        if ring[x].PassMethod == 'ThinCorrectorPass':
            ring[x].PassMethod = 'CorrectorPass'
    ad = ATAcceleratorData(ring, 1)
    lattice.set_data_source(ATLatticeDataSource(ad), pytac.SIM)
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
            lattice._data_source_manager._uc[f] = DEFAULT_UC
    return lattice
