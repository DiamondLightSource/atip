import atip
import pytac
import time as t
# import matplotlib.pyplot as plt


ring = atip.utils.load_ring
loader = atip.utils.loader
elements_by_type = atip.utils.elements_by_type
preload_at = atip.utils.preload_at
preload = atip.utils.preload


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
        if self.start_time == 0:
            raise Exception("You need to start the timer first, moron.")
        else:
            final_time = (t.time() - self.start_time)
            self.start_time = 0
            return final_time

    def time(self):
        if self.start_time == 0:
            raise Exception("You need to start the timer first, moron.")
        else:
            return (t.time() - self.start_time)


def get_sim_ring(lattice):
    return get_atsim(lattice).get_at_lattice()[:]


def get_sim_elem(elem):
    return elem._data_source_manager._data_sources[pytac.SIM]._at_element


def get_atsim(lattice):
    return lattice._data_source_manager._data_sources[pytac.SIM]._atsim


def get_thread(lattice):
    return get_atsim(lattice)._calculation_thread


def toggle_thread(lattice):
    get_atsim(lattice).toggle_calculations()


def trigger_calc(lattice):
    for elem in lattice:
        fields = list(set(elem.get_fields()[pytac.SIM]) - set(['x', 'y']))
        if len(fields) != 0:
            val = elem.get_value(fields[0], pytac.SP, data_source=pytac.SIM)
            elem.set_value(fields[0], val, data_source=pytac.SIM)
            break


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
