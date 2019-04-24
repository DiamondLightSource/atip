from pkg_resources import require
require('cothread')
require('epicsdbbuilder')
require("pytac")
require("numpy")
import numpy
import pytac
import cothread
from softioc import builder, softioc

PERIOD = 1 # s

def background_task(helper):

    while True:
        cothread.Sleep(PERIOD)
        helper.update_waveforms()

class Helper:

    def __init__(self):
        self.records = {}

    def update_waveforms(self):
        print("Updating waveforms")

        new_values = numpy.array([1]*173)
        self.records["bpm_x"].set(
            new_values
        )
        self.records["bpm_y"].set(
            new_values
        )

    def create_records(self):
        self.records["bpm_x"] = builder.Waveform('SR-DI-EBPM-01:SA:X',
                                                 initial_value=[10]*173,
                                                 NELM=173)
        self.records["bpm_y"] = builder.Waveform('SR-DI-EBPM-01:SA:Y',
                                                 initial_value=[10]*173,
                                                 NELM=173)

    def create_monitors(self):
        lattice = pytac.load_csv.load("DIAD")
        #tune_quad_families = ['Q1D', 'Q2D', 'Q3D', 'Q3B', 'Q2B', 'Q1B']
        bpm_x = lattice.get_pv_names("BPM", "x", pytac.RB)
        bpm_y = lattice.get_pv_names("BPM", "y", pytac.RB)
        bpm = bpm_x + bpm_y
        print len(bpm_x)
        print len(bpm_y)


    def monitor_callback(self):
        pass


# Create the Helper object with records and start the
helper = Helper()
helper.create_records()
helper.create_monitors()

# Start the IOC
builder.LoadDatabase()
softioc.iocInit()

# Spawn the background task to do the work
cothread.Spawn(background_task, helper)

# Enter interactive console
softioc.interactive_ioc(globals())
