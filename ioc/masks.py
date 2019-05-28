from cothread.catools import caget, caput


class camonitor_offset(object):
    def __init__(self, server, quad_pv, offset_record):
        self.server = server
        self.quad_pv = quad_pv
        self.offset_record = offset_record
        self.name = offset_record.name

    def callback(self, value, index=None):
        self.offset_record.set(value)
        self.server.refresh_record(self.quad_pv)


class callback_set(object):
    def __init__(self, output):
        self.output = output
        # If multiple outputs use last one
        for out in output:
            self.name = out.name

    def callback(self, value, index=None):
        for record in self.output:
            record.set(value)


class callback_refresh(object):
    def __init__(self, server, output_pv):
        self.server = server
        self.output_pv = output_pv
        self.name = output_pv

    def callback(self, value, index=None):
        self.server.refresh_record(self.output_pv)

    def set(self, value, index=None):
        self.server.refresh_record(self.output_pv)


class caget_mask(object):
    def __init__(self, pv):
        self.pv = pv
        self.name = pv

    def get(self):
        return caget(self.pv)


class caput_mask(object):
    def __init__(self, pv):
        self.pv = pv
        self.name = pv

    def set(self, value):
        return caput(self.pv, value)
