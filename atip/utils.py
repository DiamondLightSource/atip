import atip
import at
import pytac
import os


def load_ring(mode='DIAD'):
    filepath = os.path.join(os.path.split(os.path.dirname(__file__))[0],
                            ''.join(['rings/', mode.lower(), '.mat']))
    ring = at.load.load_mat(filepath)
    for x in range(len(ring)):
        ring[x].Index = x + 1
        ring[x].Class = ring[x].__class__.__name__
    return ring


def loader(mode='DIAD'):
    pytac_lattice = pytac.load_csv.load(mode)
    at_lattice = at.Lattice(load_ring(mode), name=pytac_lattice.name,
                            energy=3e9, periodicity=1)
    lattice = atip.load_sim.load(pytac_lattice, at_lattice)
    return lattice


def elements_by_type(lat):
    elems_dict = {t: [] for t in ['Octupole', 'Monitor', 'Dipole', 'RFCavity',
                                  'ThinMultipole', 'Aperture', 'RingParam',
                                  'Multipole', 'LongElement', 'Sextupole',
                                  'M66', 'Element', 'Drift', 'Corrector',
                                  'Bend', 'Marker', 'Quadrupole']}
    for elem in lat:
        elems_dict[type(elem).__name__].append(elem)
    return elems_dict


def preload_at(lat):
    class elems():
        pass
    setattr(elems, "all", lat)
    for elem_type, elements in elements_by_type(lat).items():
        setattr(elems, elem_type.lower() + "s", elements)
    return elems


def preload(lattice):
    """This is the only function that I think Pytac really needs.
    """
    class elems():
        pass
    setattr(elems, "all", lattice.get_elements())
    for family in lattice.get_all_families():
        setattr(elems, family.lower() + "s", lattice.get_elements(family))
    return elems
