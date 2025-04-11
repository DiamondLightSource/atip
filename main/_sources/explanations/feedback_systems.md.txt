# Feedback Systems


Currently supported "slow" feedback systems at Diamond are:

- Slow orbit feedback, SOFB;
- RF feedback, RFFB;
- Vertical Emittance Feedback, VEFB;
- and Tune Feedback, TFB.

In order to support these various feedback systems, the virtual accelerator
makes several adjustments and additions to core ATIP functionality.

## Mirrored Records:

The ability to create mirror records is provided. A mirror record can take
value(s) from one or more records as inputs and set its output dependent on
those input values. A variety of mirror types are available:

1. ``basic`` - Sets the value of the output record equal to the value of a
   single input PV.
2. ``transform`` - Applies a stored transformation to the value of its input
   PV and sets the result to its output record. Currently 'inverse'
   (``numpy.invert``) is the only supported transformation type.
3. ``collate`` - Takes the values of several input PVs, collates them into an
   array and sets this as the value of the ouptut record.
4. ``summate`` - Sums the values of several input PVs and sets the result to
   the output record.
5. ``refresher`` - Whenever an input PV changes value, the held output record
   is refreshed, by calling
   ``ATIPServer.refresh_record(output_record_pv_name)``.

For more information on mirror records see docstrings of the classes in
``mirror_objects.py``, the relevant methods on ``ATIPServer``, and
``generate_mirrored_pvs`` in ``create_csv.py``.

## Masks:

Masks are wrappers for existing functions to enable them to be addressed using
a different syntax than normal. The types of masks are:

1. ``callback_offset`` - Provides a method to be passed to as a callback. When
   called, the stored offset record is set to the passed value and the stored
   quadrupole PV is refreshed. This is the system that enables the tune
   feedback to operate, see below for more information.
2. ``callback_set`` - Provides a method to be passed to as a callback. When
   called, the stored offset records are set to the passed value.
3. ``caget_mask`` - Used to allow an existing external PV to imitate an input
   record object, ``.get()`` simply calls ``caget(stored_pv)``.
4. ``caput_mask`` - Used to allow an existing external PV to imitate an output
   record object, ``.set(value)`` simply calls ``caput(stored_pv, value)``.


## Tune feedback

As mentioned above, the ``callback_offset`` class allows the tune feedback
system to function exactly as it does on the live machine.

In the live machine, each quadrupole has an internal offset PV, whose value
is added to the setpoint PV before the setpoint is written to the hardware.
The internal offset PV monitors an offset PV which is provided by the tune
feedback system, and updates when that PV changes value. This makes clear
the distinction between changes to the setpoint which are made by the feedback
system and those which are made by manually changing the setpoint.

In the virtual accelerator, the external offset PV is monitored by the ATIP
server. If its value changes, the new value is written to the quadrupole's
internal offset record, and the quadrupole record is refreshed. This triggers
the ``_on_update`` callback of the quadrupole record, causing the new offset to
be applied to the quadrupole's value.

The tune feedback only interacts with quadrupoles, but this functionality could
also be used with any "out" record on the virtual accelerator.
