"""Module responsible for handling the loading of simulator data sources."""
import at
import pytac

from at_interface import ATSimulator
from sim_data_sources import ATElementDataSource, ATLatticeDataSource


# List of all the element fields that can be currently simulated.
SIMULATED_FIELDS = ['a1', 'b0', 'b1', 'b2', 'x', 'y', 'f', 'x_kick', 'y_kick']


def load(pytac_lattice, at_ring):
    """Load simulator data sources onto the lattice and its elements.

    Args:
        pytac_lattice (pytac.lattice.Lattice): An instance of a Pytac lattice.
        at_ring (list, str or at.lattice_object.Lattice): Accelerator Toolbox
                                                          ring, or the path to
                                                          the .mat file from
                                                          which the AT ring
                                                          can be loaded, or an
                                                          instance of an AT
                                                          lattice object.

    Returns:
        pytac.lattice.Lattice: The same Pytac lattice object, but now with a
        simulator data source fully loaded onto it.
    """
    # Load the AT(simulator) ring locally, if an AT ring was not passed.
    if isinstance(at_ring, str):
        at_ring = at.load.load_mat(at_ring)
    elif isinstance(at_ring, at.lattice.lattice_object.Lattice):
        at_ring = at_ring._lattice
    else:
        if not isinstance(at_ring, list):
            raise TypeError("Please enter a valid AT ring, AT lattice object, "
                            "or filepath to a suitable .mat file.")
    # Initialise an instance of the ATSimulator Object.
    atsim = ATSimulator(at_ring)
    atsim.start_thread()
    # Set the simulator data source on the pytac lattice.
    pytac_lattice.set_data_source(ATLatticeDataSource(atsim), pytac.SIM)
    # Load the sim onto each element.
    for e in pytac_lattice:
        # Determine which fields each simulated element should have.
        sim_fields = []
        live_fields = list(e.get_fields()[pytac.LIVE])
        for x in range(len(live_fields)):
            if live_fields[x] in SIMULATED_FIELDS:
                sim_fields.append(live_fields[x])
        # Set the simulator data source on each element.
        e.set_data_source(ATElementDataSource(at_ring[e.index-1], atsim,
                                              sim_fields), pytac.SIM)
    # Give any lattice fields not on the live machine a unit conversion object.
    for field in pytac_lattice.get_fields()[pytac.SIM]:
        if field not in pytac_lattice._data_source_manager._uc.keys():
            pytac_lattice._data_source_manager._uc[field] = pytac.load_csv.DEFAULT_UC
    return pytac_lattice
