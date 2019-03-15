import os
import argparse
import csv
import atip
import pytac

def generate_data():
    # Load the lattice and elements.
    lattice = atip.utils.loader()
    all_elements = atip.utils.preload(lattice)
    # Only keep the elements from the families that we are concerned with.
    elements = list(set(
        all_elements.hstrs
        + all_elements.vstrs
        + all_elements.bpms)
    )

    # Also get families for tune feedback
    tune_quad_elements = set(
        all_elements.q1ds
        + all_elements.q2ds
        + all_elements.q3ds
        + all_elements.q3bs
        + all_elements.q2bs
        + all_elements.q1bs
    )
    elements.extend(list(tune_quad_elements))

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
            data.append((elem.index, 'h_fofb_disabled',
                         elem.get_pv_name('h_fofb_disabled', pytac.RB), 0))
            data.append((elem.index, 'h_sofb_disabled',
                         elem.get_pv_name('h_sofb_disabled', pytac.RB), 0))
        if 'VSTR' in elem.families:
            data.append((elem.index, 'error_sum',
                         elem.get_device('y_kick').name + ':ERCSUM', 0))
            data.append((elem.index, 'state',
                         elem.get_device('y_kick').name + ':STATE', 2))
            data.append((elem.index, 'v_fofb_disabled',
                         elem.get_pv_name('v_fofb_disabled', pytac.RB), 0))
            data.append((elem.index, 'v_sofb_disabled',
                         elem.get_pv_name('v_sofb_disabled', pytac.RB), 0))
        elif 'BPM' in elem.families:
            data.append((elem.index, 'enabled',
                         elem.get_pv_name('enabled', pytac.RB), 1))
            data.append((elem.index, 'x_fofb_disabled',
                         elem.get_pv_name('x_fofb_disabled', pytac.RB), 0))
            data.append((elem.index, 'x_sofb_disabled',
                         elem.get_pv_name('x_sofb_disabled', pytac.RB), 0))
            data.append((elem.index, 'y_fofb_disabled',
                         elem.get_pv_name('y_fofb_disabled', pytac.RB), 0))
            data.append((elem.index, 'y_sofb_disabled',
                         elem.get_pv_name('y_sofb_disabled', pytac.RB), 0))
        # Add elements for Tune Feedback
        elif elem in tune_quad_elements:
            # We must build the PV name because there is no field for OFFSET1
            pv_stem = elem.get_device("b1").name
            data.append((elem.index, "OFFSET1",
                        "{}:OFFSET1".format(pv_stem), 0))

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
        "--filename",
        help="Filename for output CSV file",
        default="feedback.csv",
    )
    return parser.parse_args()

if __name__ == "__main__":

    args = parse_arguments()
    data = generate_data()
    write_data_to_file(data, args.filename)