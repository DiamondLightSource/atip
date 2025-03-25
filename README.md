[![CI](https://github.com/DiamondLightSource/atip/actions/workflows/ci.yml/badge.svg)](https://github.com/DiamondLightSource/atip/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/DiamondLightSource/atip/branch/main/graph/badge.svg)](https://codecov.io/gh/DiamondLightSource/atip)
[![PyPI](https://img.shields.io/pypi/v/atip.svg)](https://pypi.org/project/atip)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)



==============================================
ATIP - Accelerator Toolbox Interface for Pytac
==============================================

ATIP is an addition to `Pytac <https://github.com/DiamondLightSource/pytac>`_,
a framework for controlling particle accelerators. ATIP adds a simulator to
Pytac, which can be used and addressed in the same way as a real accelerator.

ATIP enables the easy offline testing of high level accelerator
controls applications, by either of two methods:

* By replacing the real accelerator at the point where it is addressed by the
  software, in the Pytac lattice object;

* In a standalone application as a "virtual accelerator", publishing the same
  control system interface as the live machine. At Diamond Light Source this
  has been implemented with EPICS, and run on a different port to the
  operational control system. So the only change required to test software is
  to configure this EPICS port.

The python implementation of
`Accelerator Toolbox <https://github.com/atcollab/at>`_ (pyAT) is used for the
simulation.

Source          | <https://github.com/DiamondLightSource/atip>
:---:           | :---:
PyPI            | `pip install atip`
Documentation   | <https://atip.readthedocs.io/en/latest/>
Releases        | <https://github.com/DiamondLightSource/atip/releases>

Installation:
-------------

See the ``INSTALL.rst`` document.

General Use:
------------

ATIP produces an "integrated lattice", which is a Pytac lattice object with a
simulation data source added. The simulated data sources are added using the
``load()`` function found in ``load_sim.py``.

This adds ``pytac.SIM`` data sources on to the lattice and each of the
elements.

The integrated lattice acts like a normal Pytac lattice; the simulator can be
referenced like the live machine but with the data source specified as
``pytac.SIM`` instead of ``pytac.LIVE``.

For example, a get request to a BPM would be
``<bpm-element>.get_value('x', data_source=pytac.SIM)``.

The simulated data sources behave exactly like the live machine, except for a
few cases. For example, the simulator has a number of lattice fields that the
live accelerator doesn't have; and the live machine has a few element fields
that the simulator doesn't.

Example
^^^^^^^

Note that you need an AT lattice that is compatible with Pytac. Some are provided
in ``atip/rings/``, otherwise try running the Matlab function
``atip/rings/create_lattice_matfile.m`` with an AT lattice loaded.

.. code-block:: python

    >>> import pytac
    >>> import atip
    >>> # Load the DIAD lattice from Pytac.
    >>> lat = pytac.load_csv.load('DIAD')
    >>> # Load the AT sim into the Pytac lattice.
    >>> atip.load_sim.load_from_filepath(lat, 'atip/rings/DIAD.mat')
    >>> # Use the sim by default.
    >>> lat.set_default_data_source(pytac.SIM)
    >>> # The initial beam position is zero.
    >>> lat.get_value('x')
    array([0., 0., 0., ..., 0., 0., 0.])
    >>> # Get the first horizontal corrector magnet and set its current to 1A.
    >>> hcor1 = lat.get_elements('HSTR')[0]
    >>> hcor1.set_value('x_kick', 1, units=pytac.ENG)
    >>> # Now the x beam position has changed.
    >>> lat.get_value('x')
    array([0.00240101, 0.00240101, 0.00239875, ..., 0.00240393, 0.00240327,
           0.00240327])
    >>>

Virtual Accelerator:
--------------------

Instructions for using ATIP as a virtual accelerator can be found in
``virtac/README.rst``.

Implementation:
---------------

All the accelerator data for the simulator is held in an ``ATSimulator``
object, which is referenced by the data sources of the lattice and each
element.Each Pytac element has an equivalent pyAT element, held in a
``ATElementDataSource``; when a get request is made, the appropriate data from
that AT element is returned.

The ``ATSimulator`` object has a queue of pending changes. When a set request
is received by an element, the element puts the changes onto the queue of the
``ATSimulator``. Inside the ``ATSimulator`` a
`Cothread <https://github.com/DiamondLightSource/cothread>`_ thread checks the
length of the queue. When it sees changes on the queue, the thread
recalculates the physics data of the lattice to ensure that it is up to date.
This means that the emittance and linear optics data held by ``ATSimulator``
is updated after every batch of changes, and that without excessive calculation
a very recent version of the lattice's physics data is always available.

API:
----

load_sim:
    * ``load_from_filepath(pytac_lattice, at_lattice_filepath, callback=None)``
      - loads the AT lattice from the given filepath to the .mat file and then
      calls ``load``.
    * ``load(pytac_lattice, at_lattice, callback=None)`` - loads the simulator
      onto the passed Pytac lattice, callback is a callable that is passed to
      ATSimulator during creation to be called on completion of each round of
      physics calculations.

ATElementDataSource:
    * ``get_fields()`` - return the fields on the element.
    * ``add_field(field)`` - add the given field to this element's data source.
    * ``get_value(field)`` - get the value for a given field on the element.
    * ``set_value(field, value)`` - set the value for a given field on the
      element, appends the change to the queue.

ATLatticeDataSource:
    * ``get_fields()`` - return the fields on the lattice.
    * ``get_value(field)`` - get the value for a given field on the lattice.
    * ``set_value(field, set_value)`` - set the value for a given field on the
      lattice, currently not supported so raises HandleException.

ATSimulator:
    * ``toggle_calculations()`` - pause or unpause the recalculation thread.
    * ``wait_for_calculations(timeout=10)`` - wait up to 'timeout' seconds for
      the current calculations to conclude, if they do it returns True, if not
      False is returned; if 'timeout' is not passed it will wait 10 seconds.
    * ``get_at_element(index)`` - return a shallow copy of the specified AT
      element from the central AT ring, N.B. An 'index' of 1 returns ring[0].
    * ``get_at_lattice()`` - return a shallow copy of the entire centralised AT
      lattice object.
    * ``get_s()`` - return the 's position' of every element in the lattice.
    * ``get_total_bend_angle()`` - return the total bending angle of all the
      dipoles in the lattice.
    * ``get_total_absolute_bend_angle()`` - return the total absolute bending
      angle of all the dipoles in the lattice.
    * ``get_energy()`` - return the energy of the lattice.
    * ``get_tune(field)`` - return the specified plane of the lattice's
      'tune'; 'x' or 'y'.
    * ``get_chromaticity(field)`` - return the specified plane of the lattice's
      'chromaticity'; 'x' or 'y'.
    * ``get_orbit(field)`` - return the specified plane of the lattice's
      'closed orbit'; 'x', 'phase_x', 'y', or 'phase_y'.
    * ``get_dispersion()`` - return the 'dispersion' vector for every element
      in the lattice.
    * ``get_alpha()`` - return the 'alpha' vector at every element in the
      lattice.
    * ``get_beta()`` - return the 'beta' vector at every element in the
      lattice.
    * ``get_mu()`` - return 'mu' at every element in the lattice.
    * ``get_m44()`` - return the 4x4 transfer matrix for every element in the
      lattice.
    * ``get_emittance(field)`` - return the specified plane of the lattice's
      'emittance'; 'x' or 'y'.
    * ``get_radiation_integrals()`` - return the 5 Synchrotron Integrals for
      the lattice.
    * ``get_momentum_compaction()`` - return the momentum compaction factor
      for the lattice.
    * ``get_energy_spread()`` - return the energy spread for the lattice.
    * ``get_energy_loss()`` - return the energy loss per turn of the lattice.
    * ``get_damping_partition_numbers()`` - return the damping partition
      numbers for the lattice's three normal modes.
    * ``get_damping_times()`` - return the damping times for the lattice's
      three normal modes.
    * ``get_linear_dispersion_action()`` - return the Linear Dispersion Action
      ("curly H") for the lattice.
    * ``get_horizontal_emittance()`` - return the horizontal ('x') emittance
      for the lattice calculated from the radiation integrals.


Specific Notes:
---------------

In order for ATIP to function correctly, the AT and Pytac lattices used must be
directly equivalent, i.e. they must have the same length and elements in the
same positions.

If local (not pip) installations are used, ATIP, AT, and Pytac must all be
located in the same source directory in order for ATIP to function correctly.

The methods on ATIP's data sources that take ``handle`` and ``throw`` arguments
do so only to conform with the Pytac ``DataSource`` base class from which they
inherit. Inside ATIP they are not used and can be ignored.

To interpret which data is to be returned or set, both ``ATElementDataSource``
and ``ATLatticeDataSource`` use a dictionary of functions corresponding to
fields. In the case where a cell needs to be passed to the data handling
functions, for further specification, functools' ``partial()`` is used.

The physics data is received from AT all together; to make it easier to manage,
it is split by ATIP and accessed by a number of methods of the ``ATSimulator``
object. This aims to be more convenient for the user but does result in the
ATSimulator object having a large number of methods.

A number of functions that perform tasks that are frequent or long-winded are
included in ``utils.py`` to make life easier for the user.
