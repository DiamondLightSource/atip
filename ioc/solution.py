import numpy
from cothread.catools import caget, caput


class callback_set(object):
    def __init__(self, output):
        self.output = output

    def callback(self, value, index=None):
        for record in self.output:
            record.set(value)


class callback_refresh(object):
    def __init__(self, server, output_pv):
        self.server = server
        self.output_pv = output_pv

    def callback(self, value, index=None):
        self.server.refresh_record(self.output_pv)


class caget_mask(object):
    def __init__(self, pv):
        self.pv = pv

    def get(self):
        return caget(self.pv)


class caput_mask(object):
    def __init__(self, pv):
        self.pv = pv

    def set(self, value):
        return caput(self.pv, value)


class summate(object):
    """This class is designed to be passed instead of a mirror record, when its
    set method is then called it takes the sum of all the input records and
    sets it to the output record.
    """
    def __init__(self, input_records, output_record):
        """
        Args:
            input_records (list): A list of records to take values from.
            output_record (pythonSoftIoc.RecordWrapper): The record to set the
                                                          sum to.
        """
        self.input_records = input_records
        self.output_record = output_record

    def set(self, value=None):
        """An imitation  of the set method of Soft-IOC records, that sums the
        values of the held input records and then sets it to the output record.
        N.B. The inital value passed by the call is discarded.
        """
        value = sum([record.get() for record in self.input_records])
        self.output_record.set(value)


class collate(object):
    """This class is designed to be passed instead of a mirror record, when its
    set method is then called it gets the values of all the input records and
    combines them in order before setting the combined array to the output
    waveform record.
    """
    def __init__(self, input_records, output_record):
        """
        Args:
            input_records (list): A list of records to take values from.
            output_record (pythonSoftIoc.RecordWrapper): The record to set the
                                                          combined array to.
        """
        self.input_records = input_records
        self.output_record = output_record

    def set(self, value=None):
        """An imitation  of the set method of Soft-IOC records, that combines
        the values of the held input records and then sets the resulting array
        to the held output record.
        N.B. The inital value passed by the call is discarded.
        """
        value = numpy.array([record.get() for record in self.input_records])
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
