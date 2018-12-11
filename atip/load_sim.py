"""Module responsible for handling the loading of simulator data sources."""
import at
import pytac
from sim_data_source import ATElementDataSource, ATLatticeDataSource, ATAcceleratorData


# List of all the element fields that can be currently simulated.
SIMULATED_FIELDS = ['a1', 'b0', 'b1', 'b2', 'x', 'y', 'f', 'x_kick', 'y_kick']


def load(lattice, ring):
    """Load simulator data sources onto the lattice and its elements.

    Args:
        lattice (pytac.lattice.Lattice): An instance of a Pytac lattice.
        ring (list/str/at.lattice_object.Lattice): An Accelerator Toolbox ring,
                                                    or the path to the .mat
                                                    file from which the AT ring
                                                    can be loaded, or an
                                                    instance of an AT lattice
                                                    object.

    Returns:
        pytac.lattice.Lattice: The same Pytac lattice object, but now with a
                                simulator data source fully loaded onto it.
    """
    # Load the AT(simulator) ring locally, if an AT ring was not passed.
    if isinstance(ring, str):
        ring = at.load.load_mat(ring)
    elif isinstance(ring, at.lattice.lattice_object.Lattice):
        ring = ring._lattice
    else:
        if not isinstance(ring, list):
            raise TypeError("Please enter a valid AT ring, AT lattice object, "
                            "or filepath to a suitable .mat file.")
    # Initialise an instance of the AT Accelerator Data Object.
    ad = ATAcceleratorData(ring)
    ad.start_thread()
    # Set the simulator data source on the lattice.
    lattice.set_data_source(ATLatticeDataSource(ad), pytac.SIM)
    # Load the sim onto each element.
    for e in lattice:
        # Determine which fields each simulated element should have.
        sim_fields = []
        live_fields = list(e.get_fields()[pytac.LIVE])
        for x in range(len(live_fields)):
            if live_fields[x] in SIMULATED_FIELDS:
                sim_fields.append(live_fields[x])
        # Set the simulator data source on each element.
        e.set_data_source(ATElementDataSource(ring[e.index-1], ad, sim_fields),
                          pytac.SIM)
    # Give any lattice fields not on the live machine a unit conversion object.
    for f in lattice.get_fields()[pytac.SIM]:
        if f not in lattice._data_source_manager._uc.keys():
            lattice._data_source_manager._uc[f] = pytac.load_csv.DEFAULT_UC
    return lattice
