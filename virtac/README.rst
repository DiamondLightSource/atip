===========================================================
Running ATIP as a Virtual Accelerator using Python Soft IOC
===========================================================

Using `PythonSoftIOC <https://github.com/Araneidae/pythonIoc>`_, ATIP can
emulate machine PVs, so that the ATIP simulator can be addressed in the same
manner as the live machine. This is useful for testing high level applications,
as it can update PVs in a physically correct way in response to changes by the
user.

The virtual accelerator (virtac for short) runs on EPICS port 6064 (the port
used by convention at Diamond for simulations) to avoid conflict with the same
PVs on the live machine.

Initialisation
--------------

Before starting please ensure you have working and up to date versions of AT,
Pytac, and ATIP - see ``../INSTALL.rst``

You must also have pythonIoc installed - https://github.com/Araneidae/pythonIoc

PythonIOC has a python interpreter linked in, and also includes some of its
dependent modules. For this reason, the ``pythonIoc`` binary has to be used
as the python interpreter for the virtac. This makes the setup a little bit
complicated. The ``start-virtac`` script handles this at Diamond.


Start the virtual accelerator
-----------------------------

Inside the virtac directory::

    $ ./start-virtac

After a minute or so, you should be presented with something like this::

    Starting record creation.
    Finished creating all 4124 records.
    Starting iocInit
    ###########################################################################
    ## EPICS R3.14.12.3 $Date: Mon 2012-12-17 14:11:47 -0600$
    ## EPICS Base built Nov  8 2018
    ###########################################################################
    iocRun: All initialization complete
    Python 2.7.3 (default, Nov  9 2013, 21:59:00) 
    [GCC 4.4.7 20120313 (Red Hat 4.4.7-3)] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    (InteractiveConsole)
    >>> 


Leave the server running and in a new terminal update the EPICS port::

    $ export EPICS_CA_SERVER_PORT=6064

In this new terminal you are then free to address the simulator as you would
the live machine, either through Pytac or by directly accessing the PVs.

Feedback Records:
-----------------

A number of PVs related to feedback systems are supported. These have been
added to aid testing of the high level applications at Diamond that control
the feedbacks, and so are site specific.

These PVs can be read in the same way as any other PV with caget, but for
testing and debugging there is a special method on the ATIP server object for
setting them.

This is done inside the server console, in the terminal where one you ran
``start-virtac`` initially). As arguments, it takes::

1. The index of an element in the ring, starting from 1; or 0 to set fields of
   the lattice;

2. The field:

   Possible element fields are:

   - ``x_fofb_disabled``
   - ``x_sofb_disabled``
   - ``y_fofb_disabled``
   - ``y_sofb_disabled``
   - ``h_fofb_disabled``
   - ``h_sofb_disabled``
   - ``v_fofb_disabled``
   - ``v_sofb_disabled``
   - ``error_sum``
   - ``enabled``
   - ``state``
   - ``offset``

   Possible lattice fields are:

   - ``beam_current``
   - ``feedback_status``
   - ``bpm_id``
   - ``emittance_status``

3. The value to be set:

   For example disabling SOFB on the first BPM::

       >>> server.set_feedback_record(3, 'enabled', 0)

   or reducing the beam current::

       >>> server.set_feedback_record(0, 'beam_current', 280)

For further information on working with feedback systems, please refer to
``FEEDBACK_SYSTEMS.rst``.

Ring Mode:
----------

You can run the virtual accelerator in any ring mode that is supported by
Pytac; currently 'VMX', 'VMXSP', and 'DIAD'. The ring mode can be set by the
following methods, which are checked in this order:

- as a command line argument to ``start-virtac``;
- by changing the ``RINGMODE`` environment variable
- a PV ``SR-CS-RING-01:MODE`` which has the ring mode as its value

If none of these is set then the virtual accelerator will default to 'DIAD'.

For example::

    $ ./start-virtac DIAD
    $ export RINGMODE=DIAD
    $ caput SR-CS-RING-01:MODE 11
    $ # Having none of these set would also start in mode 'DIAD'.
