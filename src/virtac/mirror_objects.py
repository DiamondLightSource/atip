import numpy


class summate:
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
        self.name = output_record.name

    def set(self, value=None):
        """An imitation  of the set method of Soft-IOC records, that sums the
        values of the held input records and then sets it to the output record.
        N.B. The inital value passed by the call is discarded.
        """
        value = sum([record.get() for record in self.input_records])
        self.output_record.set(value)


class collate:
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
        self.name = output_record.name

    def set(self, value=None):
        """An imitation  of the set method of Soft-IOC records, that combines
        the values of the held input records and then sets the resulting array
        to the held output record.
        N.B. The inital value passed by the call is discarded.
        """
        value = numpy.array([record.get() for record in self.input_records])
        self.output_record.set(value)


class transform:
    """This class is designed to be passed instead of a mirror record, when its
    set method is then called it applies the held transformation and then sets
    the new value to the held output record.
    """

    def __init__(self, transformation, output_record):
        """
        Args:
            transformation (typing.Callable): The transformation to be applied.
            output_record (pythonSoftIoc.RecordWrapper): The record to set the
                                                          transformed value to.
        """
        if not callable(transformation):
            raise TypeError(
                f"Transformation should be a callable, {transformation} is not."
            )
        self.output_record = output_record
        self.transformation = transformation
        self.name = output_record.name

    def set(self, value):
        """An imitation  of the set method of Soft-IOC records, that applies a
        transformation to the value before setting it to the output record.
        """
        value = numpy.asarray(value, dtype=bool)
        value = numpy.asarray(self.transformation(value), dtype=int)
        self.output_record.set(value)


class refresher:
    """This class is designed to be passed instead of a mirror record, when its
    set method is then called it refreshes the held PV on the held server.
    """

    def __init__(self, server, output_pv):
        """
        Args:
            server (atip_server.ATIPServer): The server object on which to
                                              refresh the PV.
            output_pv (str): The name of the record to refresh.
        """
        self.server = server
        self.output_pv = output_pv
        self.name = output_pv + ":REFRESH"

    def set(self, value=None):
        """An imitation  of the set method of Soft-IOC records, that refreshes
        the held output records.
        N.B. The inital value passed by the call is discarded.
        """
        self.server.refresh_record(self.output_pv)
