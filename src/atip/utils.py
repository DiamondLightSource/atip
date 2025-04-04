import os

import at
import pytac

import atip


def load_at_lattice(mode="I04", **kwargs):
    """Load an AT lattice from a .mat file in the 'rings' directory.

    .. Note:: I add custom attributes 'Index' and 'Class' to each of the
       elements in the AT lattice as I find them useful for debugging.

    Args:
        mode (str): The lattice operation mode.
        kwargs: any keyword arguments are passed to the AT lattice creator.

    Returns:
        at.lattice.Lattice: An AT lattice object.
    """
    filepath = os.path.join(
        os.path.dirname(__file__), "".join(["rings/", mode, ".mat"])
    )
    at_lattice = at.load.load_mat(filepath, name=mode, **kwargs)
    for index, elem in enumerate(at_lattice):
        elem.Index = index + 1
        elem.Class = elem.__class__.__name__
    return at_lattice


def loader(mode="I04", callback=None, disable_emittance=False):
    """Load a unified lattice of the specifed mode.

    .. Note:: A unified lattice is a Pytac lattice where the corresponding AT
       lattice has been loaded into the Pytac lattice's simulator data source
       by means of ATIP.

    Args:
        mode (str): The lattice operation mode.
        callback (typing.Callable): Callable to be called after completion of each
                              round of physics calculations in ATSimulator.
        disable_emittance (bool): Whether the emittance should be calculated.

    Returns:
        pytac.lattice.Lattice: A Pytac lattice object with the simulator data
                                source loaded.
    """
    pytac_lattice = pytac.load_csv.load(mode, symmetry=24)
    at_lattice = load_at_lattice(
        mode,
        periodicity=1,
        energy=pytac_lattice.get_value("energy"),
    )
    lattice = atip.load_sim.load(pytac_lattice, at_lattice, callback, disable_emittance)
    return lattice


def preload_at(at_lat):
    """Load the elements onto an 'elems' object's attributes by type so that
    groups of elements of the same type (class) can be more easily accessed,
    e.g. 'elems.dipole' will return a list of all the dipoles in the lattice.
    As a special case 'elems.all' will return all the elements in the lattice.

    Args:
        at_lat (at.lattice.Lattice): The AT lattice object from which to get
                                      the elements.

    returns:
        obj (class): The elems object with the elements loaded onto it by type.
    """

    class elems:
        pass

    elems.all = [elem for elem in at_lat]  # noqa: C416
    elems_dict = {
        type_: []
        for type_ in [
            "ThinMultipole",
            "Quadrupole",
            "M66",
            "Octupole",
            "Sextupole",
            "Corrector",
            "LongElement",
            "Element",
            "RFCavity",
            "Monitor",
            "Bend",
            "Marker",
            "Drift",
            "Multipole",
            "Aperture",
            "Dipole",
        ]
    }
    for elem in at_lat:
        elems_dict[type(elem).__name__].append(elem)
    for elem_type, elements in elems_dict.items():
        if len(elements) > 0:
            setattr(elems, elem_type, elements)
    return elems


def preload(pytac_lat):
    """Load the elements onto an 'elems' object's attributes by family so that
    groups of elements of the same family can be more easily accessed, e.g.
    'elems.bpm' will return a list of all the BPMs in the lattice. As a
    special case 'elems.all' will return all the elements in the lattice.

    Args:
        pytac_lat (pytac.lattice.Lattice): The Pytac lattice object from which
                                            to get the elements.

    returns:
        obj(class): The elems object with the elements loaded onto it by family.
    """

    class elems:
        pass

    elems.all = pytac_lat.get_elements()
    for family in pytac_lat.get_all_families():
        setattr(elems, family, pytac_lat.get_elements(family))
    return elems


def get_atsim(target):
    """Get the ATSimulator object being used by a unified Pytac lattice.

    Args:
        target (pytac.lattice.Lattice or ATSimulator): An ATSimulator object
                                                        or a Pytac lattice
                                                        from which an
                                                        ATSimulator object can
                                                        be extracted.

    Returns:
        ATSimulator: The simulator object performing the physics calculations.
    """
    if isinstance(target, atip.simulator.ATSimulator):
        return target
    else:  # Pytac lattice
        return target._data_source_manager._data_sources[pytac.SIM]._atsim  # noqa: SLF001


def get_sim_lattice(target):
    """Get the AT lattice that the simulator is using.

    Args:
        target (pytac.lattice.Lattice or ATSimulator): An ATSimulator object
                                                        or a Pytac lattice
                                                        from which an
                                                        ATSimulator object can
                                                        be extracted.

    Returns:
        at.lattice.Lattice: The corresponding AT lattice used by the simulator.
    """
    return get_atsim(target).get_at_lattice()


def toggle_thread(target):
    """Pause or unpause the ATSimulator calculation thread.

    Args:
        target (pytac.lattice.Lattice or ATSimulator): An ATSimulator object
                                                        or a Pytac lattice
                                                        from which an
                                                        ATSimulator object can
                                                        be extracted.
    """
    get_atsim(target).toggle_calculations()


def trigger_calc(target):
    """Manually trigger a recalculation of the physics data on the ATSimulator
    object of the given unified Pytac lattice.

    Args:
        target (pytac.lattice.Lattice or ATSimulator): An ATSimulator object
                                                        or a Pytac lattice
                                                        from which an
                                                        ATSimulator object can
                                                        be extracted.
    """
    atsim = get_atsim(target)
    atsim.trigger_calculation()
    print("Recalculation manually triggered.")
