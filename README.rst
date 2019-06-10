.. image:: https://travis-ci.org/dls-controls/atip.svg?branch=master
    :target: https://travis-ci.org/dls-controls/atip
.. image:: https://coveralls.io/repos/github/dls-controls/atip/badge.svg?branch=master
    :target: https://coveralls.io/github/dls-controls/atip?branch=master
.. image:: https://readthedocs.org/projects/atip/badge/?version=latest
    :target: https://atip.readthedocs.io/en/latest/?badge=latest

==============================================
ATIP - Accelerator Toolbox Interface for Pytac
==============================================

ATIP is intended to integrate a simulator, using the python implementation of
`AT <https://github.com/atcollab/at>`_ (pyAT), into
`Pytac <https://github.com/dls-controls/pytac>`_ so that it can be addressed
in the same manner as the live machine.

For further information on any of ATIP's functions or classes please read the
documentation `here <https://atip.readthedocs.io/en/latest/>`_.

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

ATIP can also be used as a virtual accelerator, see ``ioc/README.rst`` for
further information.

Implementation:
---------------

The accelerator data for the simulator is held in the centralised
``ATSimulator`` class, which the element and lattice data sources reference.
Each instance of ``ATElementDataSource`` holds the pyAT element equivalent of
the Pytac element that it is attached to; when a get request is made the
appropriate data from that AT element is returned, however, when a set request
is made the class puts those changes onto the queue of the centralised
``ATSimulator`` object. Inside the ``ATSimulator`` instance a cothread checks
the length of the queue, whenever a change is queued the thread recalculates
the physics data of the lattice to ensure that it is up to date. This means
that the emittance and linear optics data held by ``ATSimulator``, is updated
after every batch of changes and that without excessive calculation a very
recent version of the lattice's physics data is always available.

API:
----

load_sim:
    * ``load(lattice, ring)`` - loads the simulator onto the passed Pytac
      lattice; ring can be an AT ring, or an instance of an AT lattice object,
      or the path to a .mat file from which a ring can be loaded.

ATElementDataSource:
    * ``get_fields()`` - return the fields on the element.
    * ``get_value(field)`` - get the value for a given field on the element.
    * ``set_value(field, set_value)`` - set the value for a given field on the
      element, appends the change to the queue.
    * ``make_change(field, set_value)`` - change the value of the specifed
      field on the at element, predominantly used by the queue to make changes,
      but can also be called directly to avoid putting a change on the queue.

ATLatticeDataSource:
    * ``get_fields()`` - return the fields on the lattice.
    * ``get_value(field)`` - get the value for a given field on the lattice.
    * ``set_value(field, set_value)`` - set the value for a given field on the
      lattice.

ATSimulator:
    * ``toggle_calculations()`` - pause or unpause the recalculation thread.
    * ``wait_for_calculations(timeout)`` - wait up to 'timeout' seconds for
      the current calculations to conclude, if they do it returns True, if not
      False is returned; if 'timeout' is not passed it will wait 10 seconds.
    * ``get_at_element(index)`` - return a shallow copy of the specified AT
      element from the central AT ring, N.B. An 'index' of 1 returns ring[0].
    * ``get_at_lattice()`` - return a shallow copy of the entire centralised AT
      lattice object.
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

``ATSimulator`` has many methods because the physics data from AT must be split
into a more manageable format before it is returned, so that the user is not
given an excess of superfulous data.

A number of functions that perform tasks that are frequent or long-winded are
included in ``utils.py`` to make life easier for the user.
