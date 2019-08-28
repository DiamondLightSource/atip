ATIP - Accelerator Toolbox Interface for Pytac
==============================================

ATIP is an addition to `Pytac <https://github.com/dls-controls/pytac>`_,
a framework for controlling particle accelerators. ATIP adds a simulator to
Pytac, which can be used and addressed in the same way as a real accelerator.
This enables the easy offline testing of high level accelerator controls
applications.

ATIP is hosted on Github `here <https://github.com/dls-controls/atip>`_.

The python implementation of
`Accelerator Toolbox <https://github.com/atcollab/at>`_ (pyAT) is used
for the simulation.

.. sidebar:: How ATIP fits into the combined control structure.

    .. image:: control_structure.png
       :width: 400

ATIP allows an AT lattice to be fitted into the simulation data source of a
Pytac lattice. This integrated lattice acts like a normal Pytac lattice, and
enables the AT simulator to react and respond to changes as the real
accelerator would.

ATIP also makes use of a `Cothread <https://github.com/dls-controls/cothread>`_
thread to recalculate and update the stored physics data any time a change is
made to the lattice.

ATIP can also be run in a standalone application as a "virtual accelerator",
publishing the same control system interface as the live machine. At Diamond
Light Source this has been implemented with EPICS, using
`PythonSoftIOC <https://github.com/Araneidae/pythonIoc>`_.
This functionality is not documented here but an explanation of how it works
and how to use it may be found in the ``.rst`` files inside ATIP's ``virtac``
directory.

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
