==============================================
ATIP - Accelerator Toolbox Interface for Pytac
==============================================

ATIP is intended to integrate a simulator, using the python implementation of
`AT <https://github.com/atcollab/at>`_ (pyAT), into
`Pytac <https://github.com/dls-controls/pytac>`_ so that it can be addressed
in the same manner as the live machine.

Installation:
-------------

See the ``INSTALL.rst`` document.

General Use:
------------

The integrated ATIP lattice is created by loading the simulated data sources
onto a Pytac lattice using the ``load()`` function found in ``load_sim.py``.
Once loaded, the integrated lattice acts like a normal Pytac lattice; the
simulator is accessed through the ``pytac.SIM`` data sources on the lattice and
each of the elements. For normal operation, the simulator should be referenced
like the live machine but with the data source specified as ``pytac.SIM``
instead of ``pytac.LIVE``, i.e. a get request to a bpm would be
``<bpm-element>.get_value('x', data_source=pytac.SIM)``. It is worth noting
that generally the simulated data sources behave exactly like the live machine,
but in a few cases they do differ e.g. the simulator has a number of lattice
fields that the live accelerator doesn't have and the live machine has a few
element fields that the simulator doesn't.

Virtual Accelerator:
--------------------

ATIP can be used as a virtual accelerator, see ``SOFT-IOC.rst`` for further
information.

Implementation:
---------------

The accelerator data for the simulator is held in the centralised
``ATSimulator`` class, which the element and lattice data sources reference.
Each instance of ``ATElementDataSource`` holds the pyAT element equivalent of
the Pytac element that it is attached to; when a get request is made the
appropriate data from that AT element is returned, however, when a set request
is made the class updates its copy of that element with the changes
incorporated and then alerts the centralised ``ATSimulator`` object that new
changes have been made. Inside an ``ATSimulator`` instance a background thread
is constantly running, whenever a change is made the thread recalculates the
physics data of the lattice to ensure that it is up to date. This means that
the emittance and linear optics data held by ``ATSimulator``, is updated after
every batch of changes and that without excessive calculation a very recent
version of the lattice's physics data is always available.

API:
----

load_sim:
    * ``load(lattice, ring)`` - loads the simulator onto the passed Pytac
      lattice; ring can be an AT ring, or an instance of an AT lattice object,
      or the path to a .mat file from which a ring can be loaded.

ATElementDataSource:
    * ``get_value(field)`` - get the value for a given field on the element.
    * ``set_value(field, set_value)`` - set the value for a given field on the
      element.
    * ``get_fields()`` - return the fields on the element.

ATLatticeDataSource:
    * ``get_value(field)`` - get the value for a given field on the lattice.
    * ``set_value(field, set_value)`` - set the value for a given field on the
      lattice.
    * ``get_fields()`` - return the fields on the lattice.

ATSimulator:
    * ``start_thread()`` - start the background calculation thread.
    * ``stop_thread()`` - kill the background calculation thread after it has
      completed it's current round of calculations.
    * ``toggle_calculations()`` - pause or unpause the recalculation thread.
    * ``wait_for_calculations(timeout)`` - wait up to 'timeout' seconds for
      the current calculations to conclude.
    * ``get_element(index)`` - return a shallow copy of the specified AT
      element from the central AT ring, N.B. An 'index' of 1 returns ring[0].
    * ``get_ring()`` - return a shallow copy of the entire centralised AT ring.
    * ``get_lattice_object()`` - return a shallow of the centralised AT lattice
      object.
    * ``get_chrom(cell)`` - return the specified cell of the lattice's
      'chromaticity'; 0 for 'x', 1 for 'y'.
    * ``get_emit(cell)`` - return the specified cell of the lattice's
      'emittance'; 0 for 'x', 1 for 'y'.
    * ``get_orbit(cell)`` - return the specified cell of the lattice's closed'
      orbit'; 0 for 'x', 1 for 'phase_x', 2 for 'y', 3 for 'phase_y'.
    * ``get_tune(cell)`` - return the specified cell of the lattice's 'tune'; 0
      for 'x', 1 for 'y'.
    * ``get_disp()`` - return the 'dispersion' at every element in the lattice.
    * ``get_s()`` - return the 's position' of every element in the lattice.
    * ``get_energy()`` - return the energy of the lattice.
    * ``get_alpha()`` - return the 'alpha' vector at every element in the
      lattice.
    * ``get_beta()`` - return the 'beta' vector at every element in the
      lattice.
    * ``get_m44()`` - return the 4x4 transfer matrix for every element in the
      lattice.
    * ``get_mu()`` - return 'mu' at every element in the lattice.


Specific Notes:
---------------

In order for ATIP to function correctly; ATIP, AT, and Pytac must all be
located in the same source directory. It also goes without saying that the AT
and Pytac lattices passed to AT must be directly equivelent so that ATIP can
function correctly, i.e. same length and elements in the same positions.

Any function, in ATIP, that takes a ``handle`` argument does so only to conform
with the ``DataSource`` syntax inherited Pytac. Inside ATIP it is entirely
arbitrary and can be ignored as it is not used.

In ``ATElementDataSource``, the set value is used as a get/set flag as well as
the value to be set; if it is a get request then ``value`` is set to ``None``,
otherwise the value to be set is passed, the processing methods interpret this
and behave accordingly.

Both ``ATElementDataSource`` and ``ATLatticeDataSource`` use a dictionary of
functions that correspond to fields to interpret which data is to be returned
or set. In the case where a cell needs to be passed to the data handling
functions, for further specification, functools' ``partial()`` is used.

In ``ATSimulator``, the calculation thread makes use of threading events, which
act like flags, to indicate whether it should perform a recalculation or not;
as well as using them to start and stop the thread.

The ``start_thread()`` and ``stop_thread()`` methods on ``ATSimulator`` are
there so an ``ATSimulator`` object can exist without having the background
calculation thread running. This prevents the unnecessary wasting of processing
power when recalculation is not required.

``ATSimulator`` has many methods because the physics data from AT must be split
into a more manageable format before it is returned, so that the user is not
given an excess of superfulous data.

A number of functions that perform tasks that are frequent or long-winded are
included in ``ease.py`` to make life easier for the user.

For further information on any of ATIP's functions or classes please read the
documentation `here <https://atip.readthedocs.io/en/latest/>`_.
