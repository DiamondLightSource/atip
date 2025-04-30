# VIRTAC example

## Running ATIP as a Virtual Accelerator using Python Soft IOC

Using `PythonSoftIOC <https://github.com/Araneidae/pythonIoc>`_, ATIP can
emulate machine PVs, so that the ATIP simulator can be addressed in the same
manner as the live machine. This is useful for testing high level applications,
as it can update PVs in a physically correct way in response to changes by the
user.

The virtual accelerator (virtac for short) runs on EPICS port 6064 (the port
used by convention at Diamond for simulations) to avoid conflict with the same
PVs on the live machine.


## Starting the virtual accelerator

Once ATIP has been installed using pip or by running the docker image:

Run the virtac under the development EPICS port:

:::{code-block} bash
$ export EPICS_CA_SERVER_PORT=6064
$ export EPICS_CAS_SERVER_PORT=6064
$ export EPICS_CA_REPEATER_PORT=6065
$ # at Diamond the above can be set in one go using:    . changeports 6064
$ virtac
:::

It takes 10 seconds or so to load the interactive console::

:::{code-block} bash
Starting record creation.
~*~*Woah, were halfway there, Wo-oah...*~*~
Finished creating all 2981 records.
Starting iocInit
############################################################################
## EPICS 7.0.6.0
## Rev. 7.0.6.99.1.0
############################################################################
iocRun: All initialization complete
Python 3.7.2 (default, Jan 20 2020, 11:03:41)
[GCC 4.8.5 20150623 (Red Hat 4.8.5-39)] on linux
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>>
:::

Leave the server running and in a new terminal update the EPICS port::

:::{code-block} bash
$ export EPICS_CA_SERVER_PORT=6064
$ # or:    . changeports 6064
:::

In this new terminal you are then free to address the simulator as you would
the live machine, either through Pytac or by directly accessing the PVs.

## Command Line Options:

Usage::

    virtac [-h] [--disable-emittance] [--enable-tfb] [--verbose] [ring_mode]

Positional arguments::

    ring_mode             The ring mode to be used, e.g., IO4 or DIAD

Optional arguments::

    -h, --help            show this help message and exit
    -d, --disable-emittance
                          Disable the simulator's time-consuming emittance
                          calculation
    -t, --enable-tfb      Simulate extra dummy hardware to be used by the Tune
                          Feedback system
    -v, --verbose         Increase output and logging verbosity

N.B. The relatively slow emittance calculation is enabled by default, if the
virtac isn't as performant as your would like try disabling it using ``-d``.

## Feedback Records:

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

   - ``error_sum``
   - ``enabled``
   - ``state``
   - ``offset``
   - ``golden_offset``
   - ``bcd_offset``
   - ``bba_offset``

   Possible lattice fields are:

   - ``beam_current``
   - ``feedback_status``
   - ``bpm_id``
   - ``emittance_status``
   - ``fofb_status``
   - ``cell_<cell_number>_excite_start_times``
   - ``cell_<cell_number>_excite_amps``
   - ``cell_<cell_number>_excite_deltas``
   - ``cell_<cell_number>_excite_ticks``
   - ``cell_<cell_number>_excite_prime``

3. The value to be set:

   For example disabling SOFB on the first BPM::

:::{code-block} bash
>>> server.set_feedback_record(3, 'enabled', 0)
:::

   or reducing the beam current::

:::{code-block} bash
>>> server.set_feedback_record(0, 'beam_current', 280)
:::

For further information on working with feedback systems, please refer to
``FEEDBACK_SYSTEMS.rst``.

## Ring Mode:

You can run the virtual accelerator in any ring mode that is supported by
Pytac; currently 'VMX', 'VMXSP', 'DIAD', and 'I04'. The ring mode can be set by the
following methods, which are checked in this order:

- as a command line argument to ``virtac``;
- by changing the ``RINGMODE`` environment variable
- a PV ``SR-CS-RING-01:MODE`` which has the ring mode as its value

If none of these is set then the virtual accelerator will default to 'I04'.

For example::

:::{code-block} bash
$ virtac I04
$ export RINGMODE=I04
$ caput SR-CS-RING-01:MODE 3
$ # Having none of these set would also start in mode 'I04'.
:::
