import atip.ease as e
import at
import pytac
import matplotlib.pyplot as plt
import time


lattice = e.loader()
lattice.set_default_data_source(pytac.SIM)
elems = e.preload(lattice)


def orbit_change(index=0, value=0.1):
    old_x = []
    old_y = []
    new_x = []
    new_y = []
    for elem in elems.bpms:
        old_x.append(elem.get_value('x'))
        old_y.append(elem.get_value('y'))
    ad = e.get_ad(lattice)
    ad.toggle_calculations()
    elems.hstrs[index].set_value('x_kick', value)
    elems.vstrs[index].set_value('y_kick', value)
    ad.toggle_calculations()
    while ad.new_changes.is_set() is True:
        print("Waiting on calculations.")
        time.sleep(0.1)
    for elem in elems.bpms:
        new_x.append(elem.get_value('x'))
        new_y.append(elem.get_value('y'))
    plt.subplot(2, 2, 1)
    plt.plot(old_x)
    plt.title('old x')
    plt.subplot(2, 2, 2)
    plt.plot(old_y)
    plt.title('old y')
    plt.subplot(2, 2, 3)
    plt.plot(new_x)
    plt.title('new x')
    plt.subplot(2, 2, 4)
    plt.plot(new_y)
    plt.title('new y')
    plt.show()


def tune_change(index=0, value=70):
    old_x = lattice.get_value('tune_x')
    old_y = lattice.get_value('tune_y')
    ad = e.get_ad(lattice)
    elems.quads[index].set_value('b1', value)
    while ad.new_changes.is_set() is True:
        print("Waiting on calculations.")
        time.sleep(0.1)
    new_x = lattice.get_value('tune_x')
    new_y = lattice.get_value('tune_y')
    print("old x: {0} | new x: {1}\nold y: {2} | new y: {3}"
          .format(new_x, old_x, new_y, old_y))


def emit_change(index=0, value=0.16):
    old_x = lattice.get_value('emittance_x')
    old_y = lattice.get_value('emittance_y')
    ad = e.get_ad(lattice)
    elems.squads[index].set_value('a1', value)
    while ad.new_changes.is_set() is True:
        print("Waiting on calculations.")
        time.sleep(0.1)
    new_x = lattice.get_value('emittance_x')
    new_y = lattice.get_value('emittance_y')
    print("old x: {0} | new x: {1}\nold y: {2} | new y: {3}"
          .format(new_x, old_x, new_y, old_y))


def chrom_change(index=0, value=35):
    old_x = lattice.get_value('chromaticity_x')
    old_y = lattice.get_value('chromaticity_y')
    ad = e.get_ad(lattice)
    elems.sexts[index].set_value('b2', value)
    while ad.new_changes.is_set() is True:
        print("Waiting on calculations.")
        time.sleep(0.1)
    new_x = lattice.get_value('chromaticity_x')
    new_y = lattice.get_value('chromaticity_y')
    print("old x: {0} | new x: {1}\nold y: {2} | new y: {3}"
          .format(new_x, old_x, new_y, old_y))
