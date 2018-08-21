import pytac
import atip
import sys
import os

def loader():
    lattice = pytac.load_csv.load('VMX')
    lattice._lattice.pop()
    lattice = atip.load_sim.load(lattice)
    return lattice

def preload_all(lattice):
    class elems:
        None
    setattr(elems, "all", lattice.get_elements(None, None))
    families = list(lattice.get_all_families())
    for family in range(len(families)):
        setattr(elems, families[family].lower()+"s", lattice.get_elements(families[family]))
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

def blockPrint():
    sys.stdout = open(os.devnull, 'w')

def enablePrint():
    sys.stdout = sys.__stdout__
