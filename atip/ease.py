import atip
import at
import pytac
import time as t
import os
# import matplotlib.pyplot as plt


def ring(filepath=os.path.join(os.path.realpath(__file__),
                               os.path.realpath('ioc/diad.mat'))):
    ring = at.load.load_mat(filepath)
    for x in range(len(ring)):
        ring[x].Index = x + 1
        ring[x].Class = str(type(ring[x])).split("'")[-2].split(".")[-1]
        # Fix becasue APs are using old version of AT.
        if ring[x].PassMethod == 'ThinCorrectorPass':
            ring[x].PassMethod = 'CorrectorPass'
        if ring[x].PassMethod == 'GWigSymplecticPass':
            ring[x].PassMethod = 'DriftPass'
    return ring


def elements_by_type(lat):
    elems_dict = {}
    for elem in lat:
        elem_type = type(elem).__dict__['__doc__'].split()[1]
        if elem_type not in elems_dict:
            elems_dict[elem_type] = []
        elems_dict[elem_type].append(elem)
    return elems_dict


def preload_at(lat):
    class elems():
        pass
    setattr(elems, "all", lat)
    for elem_type, elements in elements_by_type(lat).items():
        setattr(elems, elem_type.lower() + "s", elements)
    return elems


def loader():
    lattice = pytac.load_csv.load('DIAD')
    lattice = atip.load_sim.load(lattice, at.Lattice(ring(), periodicity=1))
    return lattice


def load_vmx():
    lattice = pytac.load_csv.load('VMX')
    lattice = atip.load_sim.load(lattice,
                                 ring('../../Documents/MATLAB/vmx.mat'))
    return lattice


def preload(lattice):
    """This is the only function that I think Pytac really needs.
    """
    class elems():
        pass
    setattr(elems, "all", lattice.get_elements())
    for family in list(lattice.get_all_families()):
        setattr(elems, family.lower() + "s", lattice.get_elements(family))
    return elems


def get_attributes(obj):
    pub_attr = []
    priv_attr = []
    all_attr = obj.__dict__.keys()
    for attr in all_attr:
        if attr[0] != '_':
            pub_attr.append(attr)
        else:
            priv_attr.append(attr)
    return{'Public': pub_attr, 'Private': priv_attr}


def elements_by_field(elems, data_source=pytac.LIVE):
    """This would be the only other fucntion that I think might be useful in
        Pytac, but it's not that needed.
    """
    fields_dict = {}
    for elem in elems:
        fields = elem.get_fields()[data_source]
        for field in fields:
            if field not in fields_dict:
                fields_dict[field] = []
        fields_dict[field].append(elem.index)
    return fields_dict


class timer(object):
    def __init__(self):
        self.start_time = 0

    def start(self):
        self.start_time = t.time()

    def stop(self):
        if self.start_time is 0:
            raise Exception("You need to start the timer first, moron.")
        else:
            final_time = (t.time() - self.start_time)
            self.start_time = 0
            return final_time

    def time(self):
        if self.start_time is 0:
            raise Exception("You need to start the timer first, moron.")
        else:
            return (t.time() - self.start_time)


def get_sim_ring(lattice):
    """Ugly way to convert an AT lattice object back to a plain list.
    """
    lo = get_atsim(lattice).get_at_lattice()
    ring = []
    for i in range(len(lo)):
        ring.append(lo[i])
    return ring


def get_sim_elem(elem):
    return elem._data_source_manager._data_sources[pytac.SIM]._at_element


def get_atsim(lattice):
    return lattice._data_source_manager._data_sources[pytac.SIM]._atsim


def get_thread(lattice):
    return get_atsim(lattice)._calculation_thread


def toggle_thread(lattice):
    get_atsim(lattice).toggle_calculations()


"""
def plot_beam_position(elems, ds, x_plot=True, y_plot=True):
    # Pytac could possibly benefit from this function too.
    x = []
    y = []
    for elem in elems.bpms:
        if bool(x_plot):
            x.append(elem.get_value('x', handle=pytac.RB, data_source=ds))
        if bool(y_plot):
            y.append(elem.get_value('y', handle=pytac.RB, data_source=ds))
    if bool(x_plot) and bool(y_plot):
        plt.subplot(1, 2, 1)
        plt.plot(x)
        plt.title('X Position')
        plt.subplot(1, 2, 2)
        plt.plot(y)
        plt.title('Y Position')
        plt.show()
    elif bool(x_plot):
        plt.plot(x)
        plt.title('X Position')
        plt.show()
    elif bool(y_plot):
        plt.plot(y)
        plt.title('Y Position')
        plt.show()
    else:
        raise ValueError("Please plot at least one of x or y.")
"""


def get_defaults(lattice):
    print('Default units: {0}'.format(lattice.get_default_units()))
    print('Default data source: {0}'.format(lattice.get_default_data_source()))


def transfer(lattice):
    fields_dict = {'SQUAD': 'a1', 'SEXT': 'b2', 'QUAD': 'b1', 'BEND': 'b0',
                   'RF': 'f', 'VSTR': 'y_kick', 'HSTR': 'x_kick'}
    values = []
    toggle_thread(lattice)
    for family, field in fields_dict.items():
        print('Transfering {0}s...'.format(family.lower()))
        lattice.set_default_data_source(pytac.LIVE)
        values = lattice.get_element_values(family, field, pytac.RB)
        lattice.set_default_data_source(pytac.SIM)
        lattice.set_element_values(family, field, values)
    toggle_thread(lattice)


def class_compare(lattice, ring=None):
    pytac_to_at = {'BPM': 'Monitor', 'BPM10': 'Monitor', 'DRIFT': 'Drift',
                   'MPW12': 'Drift', 'MPW15': 'Drift', 'HCHICA': 'Corrector',
                   'VTRIM': 'Drift', 'HTRIM': 'Drift', 'AP': 'Aperture',
                   'VSTR': 'Corrector', 'HSTR': 'Corrector', 'BEND': 'Dipole',
                   'RF': 'RFCavity', 'SEXT': 'Sextupole', 'QUAD': 'Quadrupole',
                   'source': 'Marker'}  # V/HTRIM act as drifts at the moment.
    if ring is None:
        ring = get_sim_ring(lattice)
    if len(lattice) != len(ring):
        raise IndexError("Lattice and ring must be the same length.")
    results = []
    for i in range(len(lattice)):
        pytac_class = lattice[i].type_
        at_class = ring[i].Class
        if pytac_class.lower() == at_class.lower():
            results.append(True)
        else:
            pytac_mapped = pytac_to_at[pytac_class]
            if at_class.lower() != pytac_mapped.lower():
                results.append(False)
            else:
                results.append(True)
    broken = []
    for i in range(len(results)):
        if not results[i]:
            broken.append(i)
    return broken
