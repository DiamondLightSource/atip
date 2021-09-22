import csv
from warnings import warn

import atip
import numpy
import pytac
from cothread.catools import camonitor
from pytac.device import BasicDevice
from pytac.exceptions import HandleException, FieldException
from softioc import builder

from .masks import callback_set, callback_offset, caget_mask, caput_mask
from .mirror_objects import summate, collate, transform, refresher


class ATIPServer(object):
    """A soft-ioc server allowing ATIP to be interfaced using EPICS, in the
    same manner as the live machine.

    **Attributes**

    Attributes:
        lattice (pytac.lattice.Lattice): An instance of a Pytac lattice with a
                                          simulator data source.
        tune_feedback_status (bool): A boolean indicating whether the tune
                                      feedback records have been created and
                                      the monitoring systems are running.
    .. Private Attributes:
           _pv_monitoring (bool): Whether the mirrored PVs are being monitored.
           _tune_fb_csv_path (str): The path to the tune feedback .csv file.
           _in_records (dict): A dictionary containing all the created in
                                records and their associated element index and
                                Pytac field, i.e. {in_record: [index, field]}.
           _out_records (dict): A dictionary containing the names of all the
                                 created out records and their associated in
                                 records, i.e. {out_record.name: in_record}.
           _rb_only_records (list): A list of all the in records that do not
                                     have an associated out record.
           _feedback_records (dict): A dictionary containing all the feedback
                                      related records, in the same format as
                                      _in_records because they are all readback
                                      only.
           _mirrored_records (dict): A dictionary containing the PVs that the
                                      mirrored records monitor for a change
                                      and the associated mirror, in the form
                                      {monitored PV: mirror record/object}.
           _monitored_pvs (dict): A dictionary of all the PVs that are being
                                   monitored for a change and the associated
                                   camonitor object, in the form
                                   {monitored PV: camonitor object}.
           _offset_pvs (dict): A dictionary of the PVs to apply offset to and
                                their associated offset records from which to
                                get the offset from.
    """

    def __init__(
        self,
        ring_mode,
        limits_csv=None,
        feedback_csv=None,
        mirror_csv=None,
        tune_csv=None,
    ):
        """
        Args:
            ring_mode (string): The ring mode to create the lattice in.
            limits_csv (string): The filepath to the .csv file from which to
                                    load the pv limits, for more information
                                    see create_csv.py.
            feedback_csv (string): The filepath to the .csv file from which to
                                    load the feedback records, for more
                                    information see create_csv.py.
            mirror_csv (string): The filepath to the .csv file from which to
                                  load the mirror records, for more information
                                  see create_csv.py.
            tune_csv (string): The filepath to the .csv file from which to
                                load the tune feedback records, for more
                                information see create_csv.py.
        """
        self.lattice = atip.utils.loader(ring_mode, self.update_pvs)
        self.tune_feedback_status = False
        self._pv_monitoring = False
        self._tune_fb_csv_path = tune_csv
        self._in_records = {}
        self._out_records = {}
        self._rb_only_records = []
        self._feedback_records = {}
        self._mirrored_records = {}
        self._monitored_pvs = {}
        self._offset_pvs = {}
        print("Starting record creation.")
        self._create_records(limits_csv)
        if feedback_csv is not None:
            self._create_feedback_records(feedback_csv)
        if mirror_csv is not None:
            self._create_mirror_records(mirror_csv)
        print("Finished creating all {0} records.".format(len(self.all_record_names)))

    @property
    def all_record_names(self):
        """A dictionary with all the names of records created by this server
        as the keys and the corresponding record (and mirror) objects as the
        values.
        """
        mirrored = []
        for rec_list in self._mirrored_records.values():
            for record in rec_list:
                mirrored.append(record)
        all_records = (
            list(self._in_records.keys())
            + list(self._out_records.keys())
            + list(self._feedback_records.values())
            + mirrored
        )
        return {record.name: record for record in all_records}

    def update_pvs(self):
        """The callback function passed to ATSimulator during lattice creation,
        it is called each time a calculation of physics data is completed. It
        updates all the in records that do not have a corresponding out record
        with the latest values from the simulator.
        """
        for rb_record in self._rb_only_records:
            index, field = self._in_records[rb_record]
            if index == 0:
                value = self.lattice.get_value(
                    field, units=pytac.ENG, data_source=pytac.SIM
                )
                rb_record.set(value)
            else:
                value = self.lattice[index - 1].get_value(
                    field, units=pytac.ENG, data_source=pytac.SIM
                )
                rb_record.set(value)

    def _create_records(self, limits_csv):
        """Create all the standard records from both lattice and element Pytac
        fields. Several assumptions have been made for simplicity and
        efficiency, these are:
            - That bend elements all share a single PV, and are the only
               element family to do so.
            - That every field that has an out type record (SP) will also have
               an in type record (RB).
            - That all lattice fields are never setpoint and so only in records
               need to be created for them.

        Args:
            limits_csv (string): The filepath to the .csv file from which to
                                    load the pv limits.
        """
        limits_dict = {}
        if limits_csv is not None:
            csv_reader = csv.DictReader(open(limits_csv))
            for line in csv_reader:
                limits_dict[line["pv"]] = (
                    float(line["upper"]),
                    float(line["lower"]),
                    int(line["precision"]),
                )
        bend_in_record = None
        for element in self.lattice:
            if element.type_ == "BEND":
                # Create bends only once as they all share a single PV.
                if bend_in_record is None:
                    value = element.get_value(
                        "b0", units=pytac.ENG, data_source=pytac.SIM
                    )
                    get_pv = element.get_pv_name("b0", pytac.RB)
                    upper, lower, precision = limits_dict.get(
                        get_pv, (None, None, None)
                    )
                    builder.SetDeviceName(get_pv.split(":", 1)[0])
                    in_record = builder.aIn(
                        get_pv.split(":", 1)[1],
                        LOPR=lower,
                        HOPR=upper,
                        PREC=precision,
                        MDEL="-1",
                        initial_value=value,
                    )
                    set_pv = element.get_pv_name("b0", pytac.SP)
                    upper, lower, precision = limits_dict.get(
                        set_pv, (None, None, None)
                    )
                    builder.SetDeviceName(set_pv.split(":", 1)[0])
                    out_record = builder.aOut(
                        set_pv.split(":", 1)[1],
                        LOPR=lower,
                        HOPR=upper,
                        PREC=precision,
                        initial_value=value,
                        on_update_name=self._on_update,
                        always_update=True,
                    )
                    self._in_records[in_record] = ([element.index], "b0")
                    self._out_records[out_record] = in_record
                    bend_in_record = in_record
                else:
                    self._in_records[bend_in_record][0].append(element.index)
            else:
                # Create records for all other families.
                for field in element.get_fields()[pytac.SIM]:
                    value = element.get_value(
                        field, units=pytac.ENG, data_source=pytac.SIM
                    )
                    get_pv = element.get_pv_name(field, pytac.RB)
                    upper, lower, precision = limits_dict.get(
                        get_pv, (None, None, None)
                    )
                    builder.SetDeviceName(get_pv.split(":", 1)[0])
                    in_record = builder.aIn(
                        get_pv.split(":", 1)[1],
                        LOPR=lower,
                        HOPR=upper,
                        PREC=precision,
                        MDEL="-1",
                        initial_value=value,
                    )
                    self._in_records[in_record] = (element.index, field)
                    try:
                        set_pv = element.get_pv_name(field, pytac.SP)
                    except HandleException:
                        self._rb_only_records.append(in_record)
                    else:
                        upper, lower, precision = limits_dict.get(
                            set_pv, (None, None, None)
                        )
                        builder.SetDeviceName(set_pv.split(":", 1)[0])
                        out_record = builder.aOut(
                            set_pv.split(":", 1)[1],
                            LOPR=lower,
                            HOPR=upper,
                            PREC=precision,
                            initial_value=value,
                            on_update_name=self._on_update,
                            always_update=True,
                        )
                        self._out_records[out_record] = in_record
        # Now for lattice fields.
        lat_fields = self.lattice.get_fields()
        for field in set(lat_fields[pytac.LIVE]) & set(lat_fields[pytac.SIM]):
            # Ignore basic devices as they do not have PVs.
            if not isinstance(self.lattice.get_device(field), BasicDevice):
                get_pv = self.lattice.get_pv_name(field, pytac.RB)
                value = self.lattice.get_value(
                    field, units=pytac.ENG, data_source=pytac.SIM
                )
                builder.SetDeviceName(get_pv.split(":", 1)[0])
                in_record = builder.aIn(
                    get_pv.split(":", 1)[1], PREC=4, initial_value=value, MDEL="-1"
                )
                self._in_records[in_record] = (0, field)
                self._rb_only_records.append(in_record)
        print("~*~*Woah, we're halfway there, Wo-oah...*~*~")

    def _on_update(self, value, name):
        """The callback function passed to out records, it is called after
        successful record processing has been completed. It updates the out
        record's corresponding in record with the value that has been set and
        then sets the value to the centralised Pytac lattice.

        Args:
            value (number): The value that has just been set to the record.
            name (str): The name of record object that has just been set to.
        """
        in_record = self._out_records[self.all_record_names[name]]
        in_record.set(value)
        index, field = self._in_records[in_record]
        if self.tune_feedback_status is True:
            try:
                offset_record = self._offset_pvs[name]
                value += offset_record.get()
            except KeyError:
                pass
        if isinstance(index, list):
            for i in index:
                self.lattice[i - 1].set_value(
                    field, value, units=pytac.ENG, data_source=pytac.SIM
                )
        else:
            self.lattice[index - 1].set_value(
                field, value, units=pytac.ENG, data_source=pytac.SIM
            )

    def _create_feedback_records(self, feedback_csv):
        """Create all the feedback records from the .csv file at the location
        passed, see create_csv.py for more information; records for two edge
        cases are also created.

        Args:
            feedback_csv (string): The filepath to the .csv file to load the
                                    records in accordance with.
        """
        csv_reader = csv.DictReader(open(feedback_csv))
        for line in csv_reader:
            prefix, suffix = line["pv"].split(":", 1)
            builder.SetDeviceName(prefix)
            in_record = builder.aIn(suffix, initial_value=int(line["value"]), MDEL="-1")
            self._feedback_records[(int(line["index"]), line["field"])] = in_record
        # Special case: BPM ID for the x axis of beam position plot, since we
        # cannot currently create Waveform records via CSV.
        bpm_ids = [
            int(pv[2:4]) + 0.1 * int(pv[14:16])
            for pv in self.lattice.get_element_pv_names("BPM", "x", pytac.RB)
        ]
        builder.SetDeviceName("SR-DI-EBPM-01")
        bpm_id_record = builder.Waveform(
            "BPMID", NELM=len(bpm_ids), initial_value=bpm_ids
        )
        self._feedback_records[(0, "bpm_id")] = bpm_id_record
        # Special case: EMIT STATUS for the vertical emittance feedback, since
        # we cannot currently create mbbIn records via CSV.
        builder.SetDeviceName("SR-DI-EMIT-01")
        emit_status_record = builder.mbbIn(
            "STATUS", initial_value=0, ZRVL=0, ZRST="Successful", PINI="YES"
        )
        self._feedback_records[(0, "emittance_status")] = emit_status_record

    def _create_mirror_records(self, mirror_csv):
        """Create all the mirror records from the .csv file at the location
        passed, see create_csv.py for more information.

        Args:
            mirror_csv (string): The filepath to the .csv file to load the
                                    records in accordance with.
        """
        csv_reader = csv.DictReader(open(mirror_csv))
        for line in csv_reader:
            # Parse arguments.
            input_pvs = line["in"].split(", ")
            if (len(input_pvs) > 1) and (
                line["mirror type"] in ["basic", "inverse", "refresh"]
            ):
                raise IndexError(
                    "Transformation, refresher, and basic mirror "
                    "types take only one input PV."
                )
            elif (len(input_pvs) < 2) and (
                line["mirror type"] in ["collate", "summate"]
            ):
                raise IndexError(
                    "collation and summation mirror types take at"
                    " least two input PVs."
                )
            monitor = input_pvs  # need to update to support camonitor multiple
            # Convert input pvs to record objects
            input_records = []
            for pv in input_pvs:
                try:
                    input_records.append(self.all_record_names[pv])
                except KeyError:
                    input_records.append(caget_mask(pv))
            # Create output record.
            prefix, suffix = line["out"].split(":", 1)
            builder.SetDeviceName(prefix)
            if line["mirror type"] == "refresh":
                # Refresh records come first as do not require an output record
                pass
            elif line["output type"] == "caput":
                output_record = caput_mask(line["out"])
            elif line["output type"] == "aIn":
                value = float(line["value"])
                output_record = builder.aIn(suffix, initial_value=value, MDEL="-1")
            elif line["output type"] == "longIn":
                value = int(line["value"])
                output_record = builder.longIn(suffix, initial_value=value, MDEL="-1")
            elif line["output type"] == "Waveform":
                value = numpy.asarray(line["value"][1:-1].split(", "), dtype=float)
                output_record = builder.Waveform(suffix, initial_value=value)
            else:
                raise TypeError(
                    "{0} isn't a supported mirroring output type;"
                    "please enter 'caput', 'aIn', 'longIn', or "
                    "'Waveform'.".format(line["output type"])
                )
            # Update the mirror dictionary.
            for pv in monitor:
                if pv not in self._mirrored_records:
                    self._mirrored_records[pv] = []
            if line["mirror type"] == "basic":
                self._mirrored_records[monitor[0]].append(output_record)
            elif line["mirror type"] == "inverse":
                # Other transformation types are not yet supported.
                transformation = transform(numpy.invert, output_record)
                self._mirrored_records[monitor[0]].append(transformation)
            elif line["mirror type"] == "summate":
                summation_object = summate(input_records, output_record)
                for pv in monitor:
                    self._mirrored_records[pv].append(summation_object)
            elif line["mirror type"] == "collate":
                collation_object = collate(input_records, output_record)
                for pv in monitor:
                    self._mirrored_records[pv].append(collation_object)
            elif line["mirror type"] == "refresh":
                refresh_object = refresher(self, line["out"])
                self._mirrored_records[pv].append(refresh_object)
            else:
                raise TypeError(
                    "{0} is not a valid mirror type; please enter "
                    "a currently supported type from: 'basic', "
                    "'summate', 'collate', 'inverse', and "
                    "'refresh'.".format(line["mirror type"])
                )

    def monitor_mirrored_pvs(self):
        """Start monitoring the input PVs for mirrored records, so that they
        can update their value on change.
        """
        self._pv_monitoring = True
        for pv, output in self._mirrored_records.items():
            mask = callback_set(output)
            try:
                self._monitored_pvs[pv] = camonitor(pv, mask.callback)
            except Exception as e:
                warn(e)

    def refresh_record(self, pv_name):
        """For a given PV refresh the time-stamp of the associated record,
        this is done by setting the record to its current value.

        Args:
            pv_name (str): The name of the record to refresh.
        """
        try:
            record = self.all_record_names[pv_name]
        except KeyError:
            raise ValueError(
                "{0} is not the name of a record created by this "
                "server.".format(pv_name)
            )
        else:
            record.set(record.get())

    def setup_tune_feedback(self, tune_csv=None):
        """Read the tune feedback .csv and find the associated offset PVs,
        before starting monitoring them for a change to mimic the behaviour of
        the quadrupoles used by the tune feedback system on the live machine.

        Args:
            tune_csv (str): A path to a tune feedback .csv file to be used
                             instead of the default filepath passed at startup.
        """
        if tune_csv is not None:
            self._tune_fb_csv_path = tune_csv
        if self._tune_fb_csv_path is None:
            raise ValueError(
                "No tune feedback .csv file was given at "
                "start-up, please provide one now; i.e. "
                "server.start_tune_feedback('<path_to_csv>')"
            )
        csv_reader = csv.DictReader(open(self._tune_fb_csv_path))
        if not self._pv_monitoring:
            self.monitor_mirrored_pvs()
        self.tune_feedback_status = True
        for line in csv_reader:
            offset_record = self.all_record_names[line["offset"]]
            self._offset_pvs[line["set pv"]] = offset_record
            mask = callback_offset(self, line["set pv"], offset_record)
            try:
                self._monitored_pvs[line["delta"]] = camonitor(
                    line["delta"], mask.callback
                )
            except Exception as e:
                warn(e)

    def stop_all_monitoring(self):
        """Stop monitoring mirrored records and tune feedback offsets."""
        for subscription in self._monitored_pvs.values():
            subscription.close()
        self.tune_feedback_status = False
        self._pv_monitoring = False

    def set_feedback_record(self, index, field, value):
        """Set a value to the feedback in records.

        possible element fields are:
            ['x_fofb_disabled', 'x_sofb_disabled', 'y_fofb_disabled',
             'y_sofb_disabled', 'h_fofb_disabled', 'h_sofb_disabled',
             'v_fofb_disabled', 'v_sofb_disabled', 'error_sum', 'enabled',
             'state', 'offset']
        possible lattice fields are:
            ['beam_current', 'feedback_status', 'bpm_id', 'emittance_status']

        Args:
            index (int): The index of the element on which to set the value;
                          starting from 1, 0 is used to set on the lattice.
            field (string): The field to set the value to.
            value (number): The value to be set.

        Raises:
            pytac.exceptions.FieldException: If the lattice or element does
                                              not have the specified field.
        """
        try:
            self._feedback_records[(index, field)].set(value)
        except KeyError:
            if index == 0:
                raise FieldException(
                    "Lattice {0} does not have field {1}.".format(self.lattice, field)
                )
            else:
                raise FieldException(
                    "Element {0} does not have field {1}.".format(
                        self.lattice[index], field
                    )
                )
