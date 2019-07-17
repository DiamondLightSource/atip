================
Feedback Systems
================

Currently supported feedback systems at Diamond are: SOFB, RFFB, Vertical
Emittance Feedback, and Tune Feedback. In order to support these various
feedback systems the virtual accelerator makes several adjustments, these are
as follows:

Mirrored Records:
-----------------

The ability to create mirror records is provided, mirror records take value(s)
from one or more records and set their value dependant on their input. A
variety of mirror types are available::

1. ``basic`` - Sets the value of the held output record to the value of its
   single input PV.
2. ``transform`` - Applies the stored transformation to the value of its input
   PV and sets the result to it's output record. Currently 'inverse'
   (``numpy.invert``) is the only supported transformation type.
3. ``collate`` - Takes the values of its input PVs and sets them as an array to
   the ouptut record.
4. ``summate`` - Sums the values of its input PVs and sets the result to the
   output record.
5. ``refresher`` - Whenever the input PV changes value refresh the held output
   record, by calling ``ATIPServer.refresh_record(output_record_pv_name)``.

For more information on mirror records see docstrings of the classes in
``mirror_objects.py``, the relevant methods on ``ATIPServer``, and
``generate_mirrored_pvs`` in ``create_csv.py``.

Masks:
------

Masks are wrappers for existing functions to enable them to be addressed in a
different syntax than normal. The types of masks are as follows::

1. ``callback_offset`` - Provides a method to be passed to as a callback, when
   called the stored offset record is set to the passed value and the
   stored quadrupole PV is refreshed. This is the system that enables the
   tune feedback to operate, see below for more information.
2. ``callback_set`` - Provides a method to be passed to as a callback, when
   called the stored offset records are set to the passed value.
3. ``caget_mask`` - Used to allow a PV to imitate a record object, ``.get()``
   simply calls ``caget(stored_pv)``.
4. ``caput_mask`` - Used to allow a PV to imitate a record object,
   ``.set(value)`` simply calls ``caput(stored_pv, value)``.

As mentioned above the ``callback_offset`` class allows the tune feedback
system to function exactly as it does on the live machine. The external offset
PV is monitored by the server, if its value changes the new value is set to the
internal offset record and the quadrupole record is refreshed, this triggers
the ``_on_update`` callback, since the quadrupole PV has a reference to the
internal offset record stored on the server object the offset is applied to the
quadrupole's value. This functionality could be used to apply an offset to any
element out record on the server, but since we are only concerned with exactly
mimicking the tune feedback system on the live machine it is only used for
quadrupoles.
