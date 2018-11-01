import os
import sys
import atip
import pytac
import time as t
from at import load_mat
import matplotlib.pyplot as plt
from pytac.exceptions import FieldException, ControlSystemException


LATTICE_FILE = '../../Documents/MATLAB/vmx.mat'


def ring():
    ring = load_mat.load(LATTICE_FILE)
    for x in range(len(ring)):
        ring[x].Index = x+1
        # Fix becasue APs are using old version of AT.
        if ring[x].PassMethod == 'ThinCorrectorPass':
            ring[x].PassMethod = 'CorrectorPass'
    return ring


def elements_by_type(lat):
    elems_dict = {}
    for x in range(len(lat)):
        elem_type = type(lat[x]).__dict__['__doc__'].split()[1]
        if elems_dict.get(elem_type) is None:
            elems_dict[elem_type] = [lat[x]]
        else:
            elems_dict[elem_type].append(lat[x])
    return(elems_dict)


def preload_at(lat):
    class elems():
        pass
    for x in range(len(lat)):
        lat[x].Index = x+1
        lat[x].Class = lat[x].__doc__.split()[1]
    elems_dict = elements_by_type(lat)
    for x in range(len(elems_dict.keys())):
        setattr(elems, elems_dict.keys()[x].lower()+"s",
                elems_dict[elems_dict.keys()[x]])
    setattr(elems, "all", lat)
    return(elems)


def loader():
    lattice = pytac.load_csv.load('VMX')
    lattice = atip.load_sim.load(lattice, LATTICE_FILE)
    return lattice


def preload(lattice):
    class elems:
        None
    setattr(elems, "all", lattice.get_elements(None, None))
    families = list(lattice.get_all_families())
    for family in range(len(families)):
        setattr(elems, families[family].lower()+"s",
                lattice.get_elements(families[family]))
    return(elems)


def get_attributes(object):
    pub_attr = []
    priv_attr = []
    all_attr = object.__dict__.keys()
    for x in range(len(all_attr)):
        if all_attr[x][0] != '_':
            pub_attr.append(all_attr[x])
        else:
            priv_attr.append(all_attr[x])
    return({'Public': pub_attr, 'Private': priv_attr})


def block_print():
    sys.stdout = open(os.devnull, 'w')


def enable_print():
    sys.stdout = sys.__stdout__


def elements_by_field(elems):
    fields_dict = {}
    for x in range(len(elems)):
        fields = elems[x].get_fields()[pytac.LIVE]
        for y in range(len(fields)):
            if fields[y] not in fields_dict.keys():
                fields_dict[fields[y]] = []
            fields_dict[fields[y]].append(x)
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
    return lattice._data_source_manager._data_sources[pytac.SIM]._ad.get_ring()


def plot_beam_position(elems, ds, x_plot=True, y_plot=True):
    x = []
    y = []
    for elem in elems.bpms:
        if bool(x_plot):
            x.append(elem.get_value('x', data_source=ds))
        if bool(y_plot):
            y.append(elem.get_value('y', data_source=ds))
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
        raise TypeError("Please plot at least one of x or y.")


def get_defaults(lattice):
    print('Default handle: {0}'.format(lattice.get_default_handle()))
    print('Default units: {0}'.format(lattice.get_default_units()))
    print('Default data source: {0}'.format(lattice.get_default_data_source()))


def transfer(lattice):
    fields_dict = {'SEXT': ['a1', 'b2'], 'QUAD': ['b1'], 'BEND': ['b0'],
                   'RF': ['f'], 'VSTR': ['y_kick'], 'HSTR': ['x_kick']}
    for family, fields in fields_dict.items():
        elems = lattice.get_elements(family)
        for field in fields:
            for e in elems:
                try:
                    e.set_value(field, e.get_value(field, units=pytac.PHYS,
                                                   data_source=pytac.LIVE),
                                handle=pytac.SP, units=pytac.PHYS,
                                data_source=pytac.SIM)
                except FieldException:
                    raise MemoryError("This programmer's memory is clearly "
                                      "faulty as you've found a bug in pytac.")
                except (ControlSystemException, Exception):  # Tempoary.
                    print("Cannot read from {0} on {1}.".format(field, e))
    return lattice


def class_compare(lattice, ring=None):
    pytac_to_at = {'BPM': 'Monitor', 'BPM10': 'Monitor', 'DRIFT': 'Drift',
                   'MPW12': 'Drift', 'MPW15': 'Drift', 'HCHICA': 'Corrector',
                   'VTRIM': 'Drift', 'HTRIM': 'Drift', 'AP': 'Aperture',
                   'VSTR': 'Corrector', 'HSTR': 'Corrector', 'source': 'Marker',
                   'RF': 'RFCavity', 'SEXT': 'Sextupole', 'QUAD': 'Quadrupole',
                   'BEND': 'Dipole'}  # V/HTRIM act as drifts at the moment.
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
