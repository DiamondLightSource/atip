import numpy
from cothread.catools import caput, caget


class camonitor_mask(object):
    def __init__(self, output):
        self.output = output

    def callback(self, value, index=None):
        for record in self.output:
            record.set(value)


class caput_mask(object):
    def __init__(self, put_pv):
        self.put_pv = put_pv

    def set(self, value):
        caput(self.put_pv, value)


class summate(object):
    """This class is designed to be passed instead of a mirror record, when its
    set method is then called it takes the sum of all the input PVs and sets it
    to the output record.
    """
    def __init__(self, input_pvs, output_record):
        """
        Args:
            input_pvs (list): A list of PVs to take values from.
            output_record (pythonSoftIoc.RecordWrapper): The record to set the
                                                          sum to.
        """
        self.input_pvs = input_pvs
        self.output_record = output_record

    def set(self, value=None):
        """An imitation  of the set method of Soft-IOC records, that sums the
        values of the held input PVs and then sets it to the output record.
        N.B. The inital value passed by the call is discarded.
        """
        value = sum([caget(pv) for pv in self.input_pvs])
        self.output_record.set(value)


class collate(object):
    """This class is designed to be passed instead of a mirror record, when its
    set method is then called it gets the values of all the input PVs and
    combines them in order before setting the combined array to the output
    waveform record.
    """
    def __init__(self, input_pvs, output_record):
        """
        Args:
            input_pvs (list): A list of PVs to take values from.
            output_record (pythonSoftIoc.RecordWrapper): The record to set the
                                                          combined array to.
        """
        self.input_pvs = input_pvs
        self.output_record = output_record

    def set(self, value=None):
        """An imitation  of the set method of Soft-IOC records, that combines
        the values of the held input PVs and then sets the resulting array
        to the held output record.
        N.B. The inital value passed by the call is discarded.
        """
        value = numpy.array([caget(pv) for pv in self.input_pvs])
        self.output_record.set(value)


class transform(object):
    """This class is designed to be passed instead of a mirror record, when its
    set method is then called it applies the held transformation and then sets
    the new value to the held output record.
    """
    def __init__(self, transformation, output_record):
        """
        Args:
            transformation (callable): The transformation to be applied.
            output_record (pythonSoftIoc.RecordWrapper): The record to set the
                                                          transformed value to.
        """
        if not callable(transformation):
            raise TypeError("Transformation should be a callable, {0} is not."
                            .format(transformation))
        self.output_record = output_record
        self.transformation = transformation

    def set(self, value):
        """An imitation  of the set method of Soft-IOC records, that applies a
        transformation to the value before setting it to the output record.
        """
        value = numpy.asarray(value, dtype=bool)
        value = numpy.asarray(self.transformation(value), dtype=int)
        self.output_record.set(value)
