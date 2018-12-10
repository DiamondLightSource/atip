"""Module responsible for handling the loading of simulator data sources."""
import at
import pytac
from sim_data_source import ATElementDataSource, ATLatticeDataSource, ATAcceleratorData


# List of all the element fields that can be simulated.
SIMULATED_FIELDS = ['a1', 'b0', 'b1', 'b2', 'x', 'y', 'f', 'x_kick', 'y_kick']


def load(lattice, LATTICE_FILE):
    """Load simulator data sources onto the lattice and its elements.

    Args:
        lattice (pytac.lattice.Lattice): An instance of a Pytac lattice.
        LATTICE_FILE (str): The filepath to the .mat from which the Accelerator
                             Toolbox ring will be loaded.

    Returns:
        pytac.lattice.Lattice: The same Pytac lattice object, but now with a
                                simulator data source fully loaded onto it.
    """
    # Load the AT(simulator) ring locally.
    ring = at.load.load_mat(LATTICE_FILE)
    # Parse and sanitise all AT elements.
    for x in range(len(ring)):
        if not hasattr(ring[x], 'Index'):
            ring[x].Index = x + 1
            ring[x].Class = str(type(ring[x])).split("'")[-2].split(".")[-1]
        # Fix becasue APs are using old version of AT.
        if ring[x].PassMethod == 'ThinCorrectorPass':
            ring[x].PassMethod = 'CorrectorPass'
        if ring[x].PassMethod == 'GWigSymplecticPass':
            ring[x].PassMethod = 'DriftPass'
    # Initialise an instance of the AT Accelerator Data Object.
    ad = ATAcceleratorData(ring)
    ad.start_thread()
    # Set the simulator data source on the lattice.
    lattice.set_data_source(ATLatticeDataSource(ad), pytac.SIM)
    # Determine which fields each simulated element should have.
    for e in lattice:
        sim_fields = []
        live_fields = list(e.get_fields()[pytac.LIVE])
        for x in range(len(live_fields)):
            if live_fields[x] in SIMULATED_FIELDS:
                sim_fields.append(live_fields[x])
        # Set the simulator data source on each element.
        e.set_data_source(ATElementDataSource(ring[e.index-1], ad, sim_fields),
                          pytac.SIM)
    # Give any fields not on the live machine a unit conversion object.
    for f in lattice.get_fields()[pytac.SIM]:
        if f not in lattice._data_source_manager._uc.keys():
            lattice._data_source_manager._uc[f] = pytac.load_csv.DEFAULT_UC
    return lattice
