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
