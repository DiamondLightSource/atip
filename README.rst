==============================================
ATIP - Accelerator Toolbox Interface for Pytac
==============================================
ATIP is intended to integrate a simulator using the python implementation of AT, pyat, into pytac so that it can be addressed in the same manner as the live machine.

General Use:
------------
The integrated atip lattice is created by loading the simulated data sources onto a pytac lattice using the load() function found in load_sim.py. Once loaded the integrated lattice acts like a normal pytac lattice, the simulator is accessed through the pytac.SIM data sources on the lattice and each of the elements. For normal operation, the simulator should be referenced like the live machine but with the data source specified as pytac.SIM instead of pytac.LIVE, i.e. a get request to a bpm would be <bpm-element>.get_value('x', data_source=pytac.SIM). It is worth noting that generally the simulated data sources behave exactly like the live machine, but in a few cases they do differ e.g. the simulator has a number of fields that the live accelerator doesn't and the live machine has a few that the simulator doesn't.

Implementation:
---------------
The accelerator data for the simulator is held in the centralised ATAcceleratorData class which the element and lattice data sources reference. Each instance of ATElementDataSource holds the at element equivalent the pytac element it is attached to; when a get request is made the appropriate data from that at element is returned, however, when a set request is sent the class updates it's copy of that element with the changes incorporated and then it pushes that element with the new data to ATAcceleratorData. Inside that class the changed element is added to the end of a queue of changes, in the background there is a separate thread, independent of the main thread, that is constantly checking the queue, removing the oldest change from it and updating the central at ring accordingly, once the last change from the queue is processed the thread recalculates the twiss data for the ring. This means that the twiss data held by the ATAcceleratorData class, and returned from the get_twiss() method, is updated after every batch of changes and that without excessive calculation a very recent version of twiss data is always available.

API:
----
load_sim:
    * load(lattice, LATTICE_FILE) - loads the simulator onto the passed lattice object. N.B. LATTICE_FILE is the file path to the .mat file that is the AT ring is loaded from.

ATElementDataSource:
    * get_value(field, handle) - get the value for a given field on the element. N.B. The handle argument is arbitrary and can be ignored as it is not used, it is simply there to conform with the DataSource syntax in Pytac.
    * set_value(field, set_value) - set the value for a given field on the element.
    * get_fields() - return the fields on the element.

ATLatticeDataSource:
    * get_value(field, handle) - get the value for a given field on the lattice. N.B. The handle argument is arbitrary and can be ignored as it is not used, it is simply there to conform with the DataSource syntax in Pytac.
    * set_value(field, set_value) - set the value for a given field on the lattice.
    * get_fields() - return the fields on the lattice.

ATAcceleratorData:
    * push_changes(*elements) - push the changes from the individual element(s) to the centralised ring.
    * get_twiss() - returns the result of the latest twiss data calculation for the simulated lattice.
    * get_element(index) - returns a copy of the specified element from the centralised ring. N.B. An index of 1 returns the first element in the lattice, i.e. lattice[0].
    * get_ring() - returns a copy of the entire centralised ring.

Notes:
------
In order for atip to function correctly atip, at and pytac must all be installed into the same source directory; however, at and pytac can be located anywhere if the file paths to them are edited in __init__.py.

The load function in load_sim.py takes arguments of lattice, an instance of a standard pytac lattice, and LATTICE_FILE, the file path to a .mat file from which to load the accelerator data for the at simulation.

In ATElementDataSource, in sim_data_source.py, the set value is used as a get/set flag as well as the value to be set; if it is a get request value is set to numpy.nan, otherwise it is the value to be set, the processing methods interpret this and act accordingly.

In ATLatticeDataSource a complex system is used to interpret, split and return the twiss data, this is due to the format that at returns twiss data in (sequences inside a dictionary, inside a tuple); a special consideration is also made for the tune, to return only the fractional digits.

A number of functions that perform tasks that are frequent or longwinded are included in ease.py to make life easier for the user.
