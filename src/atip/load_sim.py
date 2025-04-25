"""Module responsible for handling the loading of simulator data sources."""

import at
import pytac
from pytac.exceptions import FieldException
from pytac.units import NullUnitConv

from atip.sim_data_sources import ATElementDataSource, ATLatticeDataSource
from atip.simulator import ATSimulator

# List of all the element fields that can be currently simulated.
SIMULATED_FIELDS = {"a1", "b0", "b1", "b2", "x", "y", "f", "x_kick", "y_kick"}


def load_from_filepath(
    pytac_lattice, at_lattice_filepath, callback=None, disable_emittance=False
):
    """Load simulator data sources onto the lattice and its elements.

    Args:
        pytac_lattice (pytac.lattice.Lattice): An instance of a Pytac lattice.
        at_lattice_filepath (str): The path to a .mat file from which the
                                    Accelerator Toolbox lattice can be loaded.
        callback (typing.Callable): To be called after completion of each round of
                              physics calculations.
        disable_emittance (bool): Whether the emittance should be calculated.

    Returns:
        pytac.lattice.Lattice: The same Pytac lattice object, but now with a
        simulator data source fully loaded onto it.
    """
    at_lattice = at.load.load_mat(
        at_lattice_filepath,
        name=pytac_lattice.name,
        energy=pytac_lattice.get_value("energy"),
    )
    return load(pytac_lattice, at_lattice, callback, disable_emittance)


def load(pytac_lattice, at_lattice, callback=None, disable_emittance=False):
    """Load simulator data sources onto the lattice and its elements.

    Args:
        pytac_lattice (pytac.lattice.Lattice): An instance of a Pytac lattice.
        at_lattice (at.lattice_object.Lattice): An instance of an Accelerator
                                              Toolbox lattice object.
        callback (typing.Callable): To be called after completion of each round of
                              physics calculations.
        disable_emittance (bool): Whether the emittance should be calculated.

    Returns:
        pytac.lattice.Lattice: The same Pytac lattice object, but now with a
        simulator data source fully loaded onto it.
    """
    if len(at_lattice) != len(pytac_lattice):
        raise ValueError(
            "Incompatible AT and Pytac lattices, length mismatch "
            f"(AT:{len(at_lattice)} Pytac:{len(pytac_lattice)})."
        )
    # Initialise an instance of the ATSimulator Object.
    atsim = ATSimulator(at_lattice, callback, disable_emittance)
    # Set the simulator data source on the Pytac lattice.
    pytac_lattice.set_data_source(ATLatticeDataSource(atsim), pytac.SIM)
    # Load the sim onto each element.
    for e in pytac_lattice:
        # Determine which fields each simulated element should have.
        sim_fields = list(set(e.get_fields()[pytac.LIVE]) & SIMULATED_FIELDS)
        # Set the simulator data source on each element.
        e.set_data_source(
            ATElementDataSource(at_lattice[e.index - 1], e.index, atsim, sim_fields),
            pytac.SIM,
        )
    # Give any lattice fields not on the live machine a unit conversion object.
    for field in pytac_lattice.get_fields()[pytac.SIM]:
        try:
            pytac_lattice.get_unitconv(field)
        except FieldException:
            pytac_lattice.set_unitconv(field, NullUnitConv())
    return pytac_lattice
