import argparse
import csv
import os

import pytac
from cothread.catools import caget, FORMAT_CTRL

import atip


def generate_feedback_pvs():
    # Load the lattice and elements.
    lattice = atip.utils.loader()
    all_elements = atip.utils.preload(lattice)
    # Only keep the elements from the families that we are concerned with.
    elements = list(set(
        all_elements.hstrs +
        all_elements.vstrs +
        all_elements.bpms)
    )

    # Also get families for tune feedback
    tune_quad_elements = set(
        all_elements.q1ds +
        all_elements.q2ds +
        all_elements.q3ds +
        all_elements.q3bs +
        all_elements.q2bs +
        all_elements.q1bs
    )
    elements.extend(tune_quad_elements)

    # Sort the elements by index, in ascending order.
    elements.sort(key=lambda x: x.index)
    # Data to be written is stored as a list of tuples each with structure:
    #     element index (int), field (str), pv (str), value (int).
    # We have special cases for two lattice fields that RFFB reads from.
    data = [("index", "field", "pv", "value"),
            (0, 'beam_current', 'SR-DI-DCCT-01:SIGNAL', 300),
            (0, 'feedback_status', 'CS-CS-MSTAT-01:FBSTAT', 2)]

    # Iterate over our elements to get the PV names.
    for elem in elements:
        if 'HSTR' in elem.families:
            data.append((elem.index, 'error_sum',
                         elem.get_device('x_kick').name + ':ERCSUM', 0))
            data.append((elem.index, 'state',
                         elem.get_device('x_kick').name + ':STATE', 2))
        if 'VSTR' in elem.families:
            data.append((elem.index, 'error_sum',
                         elem.get_device('y_kick').name + ':ERCSUM', 0))
            data.append((elem.index, 'state',
                         elem.get_device('y_kick').name + ':STATE', 2))
        elif 'BPM' in elem.families:
            data.append((elem.index, 'enabled',
                         elem.get_pv_name('enabled', pytac.RB), 1))
        # Add elements for Tune Feedback
        elif elem in tune_quad_elements:
            data.append((elem.index, "offset",
                         elem.get_device("b1").name + ':OFFSET1', 0))

    return data


def generate_pv_limits():
    data = [("pv", "upper", "lower", "precision")]
    lattice = atip.utils.loader()
    for element in lattice:
        for field in element.get_fields()[pytac.SIM]:
            pv = element.get_pv_name(field, pytac.RB)
            ctrl = caget(pv, format=FORMAT_CTRL)
            data.append((pv, ctrl.upper_ctrl_limit, ctrl.lower_ctrl_limit,
                         ctrl.precision))
            try:
                pv = element.get_pv_name(field, pytac.SP)
            except pytac.exceptions.HandleException:
                pass
            else:
                ctrl = caget(pv, format=FORMAT_CTRL)
                data.append((pv, ctrl.upper_ctrl_limit,
                             ctrl.lower_ctrl_limit, ctrl.precision))
    return data


def generate_mirrored_pvs():
    """
    monitor: pv(s) to be monitored, on change mirror is updated; if '' then
        the input pv(s) are monitored.
    in: pv(s) to read from, if multiple then pvs are separated by a comma and
        one space.
    out: single pv to output to, if a 'record type' is spcified then a new
        record will be created and so must not exist already.
    value: the inital value of the output record.
    record type: the type of output record to create, only 'aIn', 'longIn',
        'Waveform' types are currently supported; if '' then output to an
        existing in record already created in ATIPServer, 'caput' is also a
        special case it creates a mask for cothread.catools.caput calling
        set(value) on this mask will call caput with the output pv and the
        passed value.
    mirror type: type of mirroring to apply:
        - basic: set the value of the input record to the output record.
        - summate: sum the values of the input records and set the result to
            the output record.
        - collate: create a Waveform record from the values of the input pvs.
        - transform: apply the specified transformation function to the value
            of the input record and set the result to the output record. N.B.
            the only transformation type currently supported is 'inverse'.
    """
    lattice = atip.utils.loader()
    data = [("output type", "mirror type", "in", "out", "value")]
    # Tune PV aliases.
    tune = [lattice.get_value('tune_x', pytac.RB, data_source=pytac.SIM),
            lattice.get_value('tune_y', pytac.RB, data_source=pytac.SIM)]
    data.append(('aIn', 'basic', 'SR23C-DI-TMBF-01:X:TUNE:TUNE',
                 'SR23C-DI-TMBF-01:TUNE:TUNE', tune[0]))
    data.append(('aIn', 'basic', 'SR23C-DI-TMBF-01:Y:TUNE:TUNE',
                 'SR23C-DI-TMBF-02:TUNE:TUNE', tune[1]))
    # Combined emittance and average emittance PVs.
    emit = [lattice.get_value('emittance_x', pytac.RB, data_source=pytac.SIM),
            lattice.get_value('emittance_y', pytac.RB, data_source=pytac.SIM)]
    data.append(('aIn', 'basic', 'SR-DI-EMIT-01:HEMIT',
                 'SR-DI-EMIT-01:HEMIT_MEAN', emit[0]))
    data.append(('aIn', 'basic', 'SR-DI-EMIT-01:VEMIT',
                 'SR-DI-EMIT-01:VEMIT_MEAN', emit[1]))
    data.append(('aIn', 'summate','SR-DI-EMIT-01:HEMIT, SR-DI-EMIT-01:VEMIT',
                 'SR-DI-EMIT-01:EMITTANCE', sum(emit)))
    # Electron BPMs enabled.
    bpm_enabled_pvs = lattice.get_element_pv_names('BPM', 'enabled', pytac.RB)
    data.append(('Waveform', 'collate', ', '.join(bpm_enabled_pvs),
                 'EBPM-ENABLED:INTERIM', [0] * len(bpm_enabled_pvs)))
    data.append(('Waveform', 'inverse', 'EBPM-ENABLED:INTERIM',
                 'SR-DI-EBPM-01:ENABLED', [0] * len(bpm_enabled_pvs)))
    # BPM x positions for display on diagnostics screen.
    bpm_x_pvs = lattice.get_element_pv_names('BPM', 'x', pytac.RB)
    data.append(('Waveform', 'collate', ', '.join(bpm_x_pvs),
                 'SR-DI-EBPM-01:SA:X', [0] * len(bpm_x_pvs)))
    # BPM y positions for display on diagnostics screen.
    bpm_y_pvs = lattice.get_element_pv_names('BPM', 'y', pytac.RB)
    data.append(('Waveform', 'collate', ', '.join(bpm_y_pvs),
                 'SR-DI-EBPM-01:SA:Y', [0] * len(bpm_y_pvs)))
    return data


def generate_tune_pvs():
    lattice = atip.utils.loader()
    data = [('quad set pv', 'offset pv')]
    # Offset PV for quadrupoles in tune feedback.
    tune_pvs = []
    offset_pvs = []
    for family in ['Q1D', 'Q2D', 'Q3D', 'Q3B', 'Q2B', 'Q1B']:
        tune_pvs.extend(lattice.get_element_pv_names(family, 'b1', pytac.SP))
    for pv in tune_pvs:
        offset_pvs.append('SR-CS-TFB-01:{0}{1}{2}:I'.format(pv[2:4], pv[9:12],
                                                            pv[13:15]))
    for offset_pv, tune_pv in zip(offset_pvs, tune_pvs):
        data.append((tune_pv, offset_pv))
    return data


def write_data_to_file(data, filename):
    # Write the collected data to the .csv file.
    if not filename.endswith('.csv'):
        filename += '.csv'
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, filename), "wb") as file:
        csv_writer = csv.writer(file)
        csv_writer.writerows(data)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Generate CSV file to define the PVs served by the "
                    "virtual accelerator IOC."
    )
    parser.add_argument(
        "--feedback",
        help="Filename for output feedback pvs CSV file",
        default="feedback.csv",
    )
    parser.add_argument(
        "--limits",
        help="Filename for output pv limits CSV file",
        default="limits.csv",
    )
    parser.add_argument(
        "--mirrored",
        help="Filename for output pv limits CSV file",
        default="mirrored.csv",
    )
    parser.add_argument(
        "--tune",
        help="Filename for output pv limits CSV file",
        default="tunefb.csv",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    data = generate_feedback_pvs()
    write_data_to_file(data, args.feedback)
    data = generate_pv_limits()
    write_data_to_file(data, args.limits)
    data = generate_mirrored_pvs()
    write_data_to_file(data, args.mirrored)
    data = generate_tune_pvs()
    write_data_to_file(data, args.tune)
