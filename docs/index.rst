ATIP - Accelerator Toolbox Interface for Pytac
==============================================

ATIP is intended to integrate a simulator, using the python implementation of
`AT <https://github.com/atcollab/at>`_ (pyAT), into
`Pytac <https://github.com/dls-controls/pytac>`_ so that it can be addressed
in the same manner as the live machine. ATIP is hosted on GitHub, found
`here. <https://github.com/dls-controls/atip>`_

.. sidebar:: How ATIP fits into the combined control structure.

    .. image:: control_structure.png
       :width: 400

ATIP allows an AT lattice to be fitted into the simulation data source of a
Pytac lattice. This integrated lattice acts like a normal Pytac lattice, and
enables the AT simulator to react and respond to changes as the live machine
would.

ATIP also makes use of `Cothread <https://github.com/dls-controls/cothread>`_
to recalculate the physics data any time a change is made to the lattice.

ATIP can be run as a virtual accelerator, this functionality is not documented
here but and explanation of how it works and how to use it may be found in the
.rst files inside ATIP's virtac directory. To communicate with EPICS the ATIP
uses `PythonSoftIOC <https://github.com/Araneidae/pythonIoc>`_, this enables it
to emulate all the PVs of the live machine.

Contents:
=========

.. toctree::
   :maxdepth: 2

   self
   atip


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
