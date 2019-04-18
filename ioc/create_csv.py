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
            # We must build the PV name because there is no field for OFFSET1
            pv_stem = elem.get_device("b1").name
            data.append((elem.index, "OFFSET1",
                        "{}:OFFSET1".format(pv_stem), 0))

    return data


def generate_pv_limits():
    data = [("pv", "upper", "lower")]
    lattice = atip.utils.loader()
    for element in lattice:
        for field in element.get_fields()[pytac.SIM]:
            pv = element.get_pv_name(field, pytac.RB)
            ctrl = caget(pv, format=FORMAT_CTRL)
            data.append((pv, ctrl.upper_ctrl_limit, ctrl.lower_ctrl_limit))
            try:
                pv = element.get_pv_name(field, pytac.SP)
            except pytac.exceptions.HandleException:
                pass
            else:
                ctrl = caget(pv, format=FORMAT_CTRL)
                data.append((pv, ctrl.upper_ctrl_limit,
                             ctrl.lower_ctrl_limit))
    return data


def write_data_to_file(data, filename):
    # Write the collected data to the .csv file.
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
        default="pv_limits.csv",
    )
    return parser.parse_args()


if __name__ == "__main__":

    args = parse_arguments()
    data = generate_feedback_pvs()
    write_data_to_file(data, args.feedback)
    data = generate_pv_limits()
    write_data_to_file(data, args.limits)
