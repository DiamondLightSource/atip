===========================================================
Running ATIP as a Virtual Accelerator using Python Soft IOC
===========================================================

Using Python Soft IOC ATIP can emulate machine PVs so that the ATIP simulator
can be addressed in the same manner as the live machine. This is useful for
testing high level applications as it can update PVs in a physically correct
way in response to changes by the user. The virtual accelerator runs on EPICS
port 6064 to avoid conflict with the same PVs on the live machine.

Initialisation:
---------------

Before starting please ensure you have working up to date versions of Pytac,
AT, and ATIP.

Inside the top-level atip directory::

    $ ./start-ioc


After a minute or two, you should be presented with something like this::

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


In this terminal you are then free to address the simulator as you would the
live machine, either through Pytac or by directly accessing the PVs.

Feedback Records:
-----------------

A number of PVs related to the feedback systems are supported. They can be read
from in the same way as any other PV, but for testing and debugging there is a
special method for setting them. This is done on the ATIP server object, inside
the server terminal. As arguments, it takes the element's index in the ring
(starting from 1, 0 is used to set on the lattice), the field (possible fields
are:
    'x_fofb_disabled', 'x_sofb_disabled', 'y_fofb_disabled', 'y_sofb_disabled',
    'h_fofb_disabled', 'h_sofb_disabled', 'v_fofb_disabled', 'v_sofb_disabled',
    'error_sum', 'enabled', 'state', 'beam_current', feedback_status'
), and the value to be set.

For example disabling SOFB on the first BPM, or reducing the beam current::

    >>> server.set_feedback_record(3, 'enabled', 0)
    >>> server.set_feedback_record(0, 'beam_current', 280)
