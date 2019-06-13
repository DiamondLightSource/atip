import atip
import at
import pytac
import os


def load_at_lattice(mode='DIAD', **kwargs):
    """Load an AT lattice from a .mat file in the 'rings' directory.

    .. Note:: I add custom attributes 'Index' and 'Class' to the each of the
       elements in the AT lattice as I find them useful for debugging.

    Args:
        mode (str): The lattice operation mode.
        kwargs: any keyword arguments are passed to the AT lattice creator.

    Returns:
        at.lattice.Lattice: An AT lattice object.
    """
    filepath = os.path.join(os.path.split(os.path.dirname(__file__))[0],
                            ''.join(['rings/', mode.lower(), '.mat']))
    at_lattice = at.load.load_mat(filepath, **kwargs)
    for x in range(len(at_lattice)):
        at_lattice[x].Index = x + 1
        at_lattice[x].Class = at_lattice[x].__class__.__name__
    return at_lattice


def loader(mode='DIAD', callback=None):
    """Load a unified lattice of the specifed mode.

    .. Note:: A unified lattice is a Pytac lattice where the corresponding AT
       lattice has been loaded into the Pytac lattice's simulator data source
       by means of ATIP.

    Args:
        mode (str): The lattice operation mode.
        callback (callable): Callable to be called after completion of each
                              round of physics calculations in ATSimulator.

    Returns:
        pytac.lattice.Lattice: A Pytac lattice object with the simulator data
                                source loaded.
    """
    pytac_lattice = pytac.load_csv.load(mode, symmetry=24)
    at_lattice = load_at_lattice(mode, name=pytac_lattice.name, periodicity=1,
                                 energy=pytac_lattice.get_value('energy'))
    lattice = atip.load_sim.load(pytac_lattice, at_lattice, callback)
    return lattice


def preload_at(at_lat):
    """Load the elements onto an 'elems' object's attributes by type so that
    groups of elements of the same type (class) can be more easily accessed,
    e.g. 'elems.dipoles' will return a list of all the dipoles in the lattice.
    As a special case 'elems.all' will return all the elements in the lattice.

    Args:
        at_lat (at.lattice.Lattice): The AT lattice object from which to get
                                      the elements.

    returns:
        obj: The elems object with the elements loaded onto it by type.
    """
    class elems():
        pass
    setattr(elems, "all", [elem for elem in at_lat])
    elems_dict = {type_: [] for type_ in ['ThinMultipole', 'Quadrupole', 'M66',
                                          'Octupole', 'Sextupole', 'Corrector',
                                          'LongElement', 'Element', 'RFCavity',
                                          'Monitor', 'Bend', 'Marker', 'Drift',
                                          'Multipole', 'Aperture', 'Dipole']}
    for elem in at_lat:
        elems_dict[type(elem).__name__].append(elem)
    for elem_type, elements in elems_dict.items():
        setattr(elems, elem_type.lower() + "s", elements)
    return elems


def preload(pytac_lat):
    """Load the elements onto an 'elems' object's attributes by family so that
    groups of elements of the same family can be more easily accessed, e.g.
    'elems.bpms' will return a list of all the BPMs in the lattice. As a
    special case 'elems.all' will return all the elements in the lattice.

    Args:
        pytac_lat (pytac.lattice.Lattice): The Pytac lattice object from which
                                            to get the elements.

    returns:
        obj: The elems object with the elements loaded onto it by family.
    """
    class elems():
        pass
    setattr(elems, "all", pytac_lat.get_elements())
    for family in pytac_lat.get_all_families():
        setattr(elems, family.lower() + "s", pytac_lat.get_elements(family))
    return elems


def get_atsim(pytac_lattice):
    """Get the ATSimulator object being used by a unified Pytac lattice.

    Args:
        pytac_lattice (pytac.lattice.Lattice): An instance of a unified Pytac
                                                lattice from which to get the
                                                ATSimulator object being used.

    Returns:
        ATSimulator: The simulator object performing the physics calculations.
    """
    return pytac_lattice._data_source_manager._data_sources[pytac.SIM]._atsim


def get_sim_lattice(pytac_lattice):
    """Get the AT lattice that the simulator is using.

    Args:
        pytac_lattice (pytac.lattice.Lattice): An instance of a unified Pytac
                                                lattice from which to get the
                                                corresponding AT lattice.

    Returns:
        at.lattice.Lattice: The corresponding AT lattice used by the simulator.
    """
    return get_atsim(pytac_lattice).get_at_lattice()


def get_thread(pytac_lattice):
    """Get the Cothread thread that is used for performing the recalculations.

    Args:
        pytac_lattice (pytac.lattice.Lattice): An instance of a unified Pytac
                                                lattice from which to get the
                                                calculation thread off of the
                                                ATSimulator object.

    Returns:
        cothread.Thread: The calculation thread that the Pytac lattice's
                         ATSimulator object uses to recalculate physics data.
    """
    return get_atsim(pytac_lattice)._calculation_thread


def toggle_thread(pytac_lattice):
    """Pause or unpause the ATSimulator calculation thread.

    Args:
        pytac_lattice (pytac.lattice.Lattice): An instance of a unified Pytac
                                                lattice from which to pause or
                                                unpause the calculation thread
                                                on its ATSimulator object.
    """
    get_atsim(pytac_lattice).toggle_calculations()


def trigger_calc(pytac_lattice):
    """Manually trigger a recalculation of the physics data on the ATSimulator
    object of the given unified Pytac lattice.

    Args:
        pytac_lattice (pytac.lattice.Lattice): An instance of a unified Pytac
                                                lattice from which to trigger a
                                                recalculation of the physics
                                                data on its ATSimulator object.
    """
    for elem in pytac_lattice:
        fields = list(set(elem.get_fields()[pytac.SIM]) - set(['x', 'y']))
        if len(fields) != 0:
            val = elem.get_value(fields[0], pytac.SP, data_source=pytac.SIM)
            elem.set_value(fields[0], val, data_source=pytac.SIM)
            print("Recalculation manually triggered.")
            break
