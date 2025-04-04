from cothread.catools import caget, caput


class callback_offset:
    """A class to hold a method to be passed as a callback to camonitor."""

    def __init__(self, server, quad_pv, offset_record):
        """
        Args:
            server (atip_server.ATIPServer): The server object on which to
                                              refresh the PVs.
            quad_pv (str): The name of the PV to refresh so it can have the new
                            offset applied, in the case of tune feedback this
                            is always a quadrupole.
            offset_record (pythonSoftIoc.RecordWrapper): The record to set the
                                                          offset to.
        """
        self.server = server
        self.quad_pv = quad_pv
        self.offset_record = offset_record

    def callback(self, value, index=None):
        """When called set the passed value to the held offset record and
        refresh the held quadrupole PV so the new offset is applied.

        Args:
            value (number): The value to set to the offset record.
            index (int): Ignored, only there to support camonitor multiple.
        """
        self.offset_record.set(value)
        self.server.refresh_record(self.quad_pv)


class callback_set:
    """A class to hold a method to be passed as a callback to camonitor."""

    def __init__(self, output):
        """
        Args:
            output (list): A list of output records to set to.
        """
        self.output = output

    def callback(self, value, index=None):
        """When called set the passed value to all held output records.

        Args:
            value (number): The value to set to the outupt records.
            index (int): Ignored, only there to support camonitor multiple.
        """
        for record in self.output:
            record.set(value)


class caget_mask:
    """A mask for caget so it can comply with the record.get() syntax."""

    def __init__(self, pv):
        """
        Args:
            pv (str): The PV to call caget on.
        """
        self.pv = pv
        self.name = pv

    def get(self):
        return caget(self.pv)


class caput_mask:
    """A mask for caput so it can comply with the record.set(value) syntax."""

    def __init__(self, pv):
        """
        Args:
            pv (str): The PV to call caput on.
        """
        self.pv = pv
        self.name = pv

    def set(self, value):
        """
        Args:
            value (number): The value to caput to the PV.
        """
        return caput(self.pv, value)
