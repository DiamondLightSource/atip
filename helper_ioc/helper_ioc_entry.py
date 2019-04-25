from pkg_resources import require
require('cothread')
require('epicsdbbuilder')
require("pytac")
require("numpy")
import numpy
import logging
import pytac
import cothread
from softioc import builder, softioc

# Periods for the background tasks to run
PERIOD_SLOW = 1.0 # s
PERIOD_FAST = 0.1 # s

def slow_background_task(helper):

    while True:
        cothread.Sleep(PERIOD_SLOW)
        helper.update_waveforms()

def fast_background_task(helper):

    while True:
        cothread.Sleep(PERIOD_FAST)
        helper.update_tunes()

class Helper:

    def __init__(self):
        self.records = {}
        self.monitors = {}
        self.quadrupoles = {}

        self.lattice = pytac.load_csv.load("DIAD")

    def update_waveforms(self):

        for key in ["bpm_x", "bpm_y"]:
            self.records[key].set(
                numpy.array(self.monitors[key].cached_value)
            )

    def update_tunes(self):

        for key in ["tune_x", "tune_y"]:
            self.records[key].set(
                self.monitors[key].cached_value
            )


    def create_records(self):
        logging.info("Create records")
        # BPM waveforms for display on Diagnostics screen
        self.records["bpm_x"] = builder.Waveform('SR-DI-EBPM-01:SA:X',
                                                 initial_value=[10.0]*173,
                                                 NELM=173,
                                                 FTVL="DOUBLE")
        self.records["bpm_y"] = builder.Waveform('SR-DI-EBPM-01:SA:Y',
                                                 initial_value=[10.0]*173,
                                                 NELM=173,
                                                 FTVL="DOUBLE")
        self.records["bpm_id"] = builder.Waveform("SR-DI-EBPM-01:BPMID",
                                                  initial_value=[0.0]*173,
                                                  NELM=173,
                                                  FTVL="DOUBLE")

        # We must provide aliases for tune PVs
        self.records["tune_x"] = builder.aIn("SR23C-DI-TMBF-01:TUNE:TUNE",
                                             initial_value=0.0)
        self.records["tune_y"] = builder.aIn("SR23C-DI-TMBF-02:TUNE:TUNE",
                                             initial_value=0.0)

    def create_monitors(self):
        logging.info("Create monitors")
        # Set up monitors for BPMs
        bpm_x = self.lattice.get_pv_names("BPM", "x", pytac.RB)
        bpm_y = self.lattice.get_pv_names("BPM", "y", pytac.RB)

        self.monitors["bpm_x"] = MonitoredPvList(bpm_x)
        self.monitors["bpm_y"] = MonitoredPvList(bpm_y)

        bpm_ids = []
        for pv in bpm_x:
            prefix = pv.split(':')[0]
            cell = int(prefix[2:4])
            index = int(prefix[14:17])
            bpm_ids.append(cell + 0.1 * index)

        # Initialise the BPM ID waveform for the X-axis of the plot
        self.records["bpm_id"].set(numpy.array(bpm_ids))

        # Set up monitors for tune PVs
        self.monitors["tune_x"] = MoniotredPV("SR23C-DI-TMBF-01:X:TUNE:TUNE")
        self.monitors["tune_y"] = MoniotredPV("SR23C-DI-TMBF-01:Y:TUNE:TUNE")

    def create_quadrupoles(self):
        logging.info("Create quadrupoles")
        # Get tune quadrupole PVs
        tune_quad_families = ['Q1D', 'Q2D', 'Q3D', 'Q3B', 'Q2B', 'Q1B']
        tune_pvs = []

        logging.info("Get target PV names")
        for family in tune_quad_families:
            tune_pvs = tune_pvs + self.lattice.get_pv_names(
                family,
                "b1",
                pytac.SP
            )
        logging.info("Create Quadrupoles")
        for target_pv in tune_pvs:
            pieces=dict(
                cell = target_pv[2:4],
                family = target_pv[9:12],
                index = target_pv[13:15]
            )
            monitored_pv = "SR-CS-TFB-01:{cell}{family}{index}:I".format(
                **pieces
            )
            self.quadrupoles[target_pv] = Quadrupole(target_pv, monitored_pv)


class MonitoredPvList:

    def __init__(self, pv_name_list):
        self.cached_value = [0] * len(pv_name_list)
        self.nonitor = cothread.catools.camonitor(pv_name_list, self.monitor_callback)

    def monitor_callback(self, value, index):
        self.cached_value[index] = value


class MoniotredPV:
    def __init__(self, pv_name):
        self.cached_value = 0
        self.monitor = cothread.catools.camonitor(pv_name, self.monitor_callback)

    def monitor_callback(self, value):
        self.cached_value = value


class Quadrupole(MoniotredPV):
    def __init__(self, target_pv, monitor_pv):
        self.target_pv = target_pv
        self.monitored_pv = monitor_pv
        self.original_value = cothread.catools.caget(target_pv)
        self.offset = 0.0
        logging.info("Init monitor %s target %s", monitor_pv, target_pv)
        MoniotredPV.__init__(self, self.monitored_pv)

    def monitor_callback(self, value):
        """Override the callback from the base class"""
        self.apply_updated_offset(value)

    def apply_updated_offset(self, new_offset):
        self.offset = new_offset
        new_value = self.original_value + self.offset
        logging.debug("caput %s %d",self.target_pv, new_value)
        cothread.catools.caput(self.target_pv, new_value)

def main():

    logging.basicConfig(level=logging.INFO)

    # Create the Helper object with records
    helper = Helper()
    helper.create_records()
    helper.create_monitors()
    helper.create_quadrupoles()

    # Start the IOC
    builder.LoadDatabase()
    softioc.iocInit()

    # Spawn the background tasks to do the work
    cothread.Spawn(slow_background_task, helper)
    cothread.Spawn(fast_background_task, helper)

    # Enter interactive console
    softioc.interactive_ioc(globals())

if __name__ == "__main__":
    main()