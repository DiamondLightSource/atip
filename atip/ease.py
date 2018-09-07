import pytac
import atip
import sys
import os
from at import load_mat
import time as t


LATTICE_FILE = './vmx.mat'


def ring():
    ring = load_mat.load(LATTICE_FILE)
    for x in range(len(ring)):
        ring[x].Index = x+1
        ring[x].Class = ring[x].__doc__.split()[1]
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
    lattice = atip.load_sim.load(lattice)
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
        self.end_time = 0

    def start(self):
        self.start_time = t.time()

    def stop(self):
        self.end_time = t.time()

    def time(self):
        return (self.end_time - self.start_time)
