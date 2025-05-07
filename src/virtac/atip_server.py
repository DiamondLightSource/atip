import csv
import logging
import typing
from warnings import warn

import numpy
import pytac
from cothread.catools import camonitor
from pytac.device import SimpleDevice
from pytac.exceptions import FieldException, HandleException
from softioc import builder

import atip

from .masks import caget_mask, callback_offset, callback_set, caput_mask
from .mirror_objects import collate, refresher, summate, transform


class ATIPServer:
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
                                records, a list of associated element indexes and
                                Pytac field, i.e. {in_record: [[index], field]}.
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
            _record_names (dict[str: softioc.builder.record]): A dictonary
                                containing the name of every pv created by the
                                virtual accelerator and the pv object itself.
    """

    def __init__(
        self,
        ring_mode,
        limits_csv=None,
        bba_csv=None,
        feedback_csv=None,
        mirror_csv=None,
        tune_csv=None,
        disable_emittance=False,
    ):
        """
        Args:
            ring_mode (str): The ring mode to create the lattice in.
            limits_csv (str): The filepath to the .csv file from which to
                                    load the pv limits, for more information
                                    see create_csv.py.
            bba_csv (str): The filepath to the .csv file from which to
                                    load the bba records, for more
                                    information see create_csv.py.
            feedback_csv (str): The filepath to the .csv file from which to
                                    load the feedback records, for more
                                    information see create_csv.py.
            mirror_csv (str): The filepath to the .csv file from which to
                                  load the mirror records, for more information
                                  see create_csv.py.
            tune_csv (str): The filepath to the .csv file from which to
                                load the tune feedback records, for more
                                information see create_csv.py.
            disable_emittance (bool): Whether the emittance should be disabled.
        """
        self.lattice = atip.utils.loader(ring_mode, self.update_pvs, disable_emittance)
        self.tune_feedback_status = False
        self._pv_monitoring = False
        self._tune_fb_csv_path = tune_csv
        self._in_records = {}
        self._out_records = {}
        self._rb_only_records = []
        self._bba_records = {}
        self._feedback_records = {}
        self._mirrored_records = {}
        self._monitored_pvs = {}
        self._offset_pvs = {}
        self._record_names = {}
        print("Starting record creation.")
        self._create_records(limits_csv, disable_emittance)
        if bba_csv is not None:
            self._create_bba_records(bba_csv)
        if feedback_csv is not None:
            self._create_feedback_records(feedback_csv, disable_emittance)
        if mirror_csv is not None:
            self._create_mirror_records(mirror_csv)
        print(f"Finished creating all {len(self._record_names)} records.")

    def _update_record_names(self, records):
        """Updates _record_names using the supplied list of softioc record objects."""
        self._record_names |= {record.name: record for record in list(records)}

    def update_pvs(self):
        """The callback function passed to ATSimulator during lattice creation,
        it is called each time a calculation of physics data is completed. It
        updates all the in records that do not have a corresponding out record
        with the latest values from the simulator.
        """
        logging.debug("Updating output PVs")
        for rb_record in self._rb_only_records:
            indexes, field = self._in_records[rb_record]
            # indexes is a list of element indexes associated with the pv
            # index 0 is the lattice itself rather than an element
            for index in indexes:
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

    def _create_records(self, limits_csv, disable_emittance):
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
            limits_csv (str): The filepath to the .csv file from which to
                                    load the pv limits.
            disable_emittance (bool): Whether the emittance related PVs should be
                                        created or not.
        """
        limits_dict = {}
        if limits_csv is not None:
            with open(limits_csv) as f:
                csv_reader = csv.DictReader(f)
                for line in csv_reader:
                    limits_dict[line["pv"]] = (
                        float(line["upper"]),
                        float(line["lower"]),
                        int(line["precision"]),
                        float(line["drive high"]),
                        float(line["drive low"]),
                    )

        bend_in_record = None
        for element in self.lattice:
            # There is only 1 bend PV in the lattice, if it has already been defined and
            # we have another bend element, then just register this element with the
            # existing pv. Otherwise create a new PV for the element
            if element.type_.upper() == "BEND" and bend_in_record is not None:
                self._in_records[bend_in_record][0].append(element.index)
            else:
                for field in element.get_fields()[pytac.SIM]:
                    value = element.get_value(
                        field, units=pytac.ENG, data_source=pytac.SIM
                    )
                    get_pv = element.get_pv_name(field, pytac.RB)
                    upper, lower, precision, drive_high, drive_low = limits_dict.get(
                        get_pv, (None, None, None, None, None)
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
                    self._in_records[in_record] = ([element.index], field)

                    try:
                        set_pv = element.get_pv_name(field, pytac.SP)
                    except HandleException:
                        self._rb_only_records.append(in_record)
                    else:
                        upper, lower, precision, drive_high, drive_low = (
                            limits_dict.get(set_pv, (None, None, None, None, None))
                        )
                        builder.SetDeviceName(set_pv.split(":", 1)[0])
                        out_record = builder.aOut(
                            set_pv.split(":", 1)[1],
                            DRVH=drive_high,
                            DRVL=drive_low,
                            LOPR=lower,
                            HOPR=upper,
                            PREC=precision,
                            initial_value=value,
                            on_update_name=self._on_update,
                            always_update=True,
                        )
                        self._out_records[out_record] = in_record
                        if element.type_.upper() == "BEND" and bend_in_record is None:
                            bend_in_record = in_record

        # Now for lattice fields.
        lat_fields = self.lattice.get_fields()
        lat_fields = set(lat_fields[pytac.LIVE]) & set(lat_fields[pytac.SIM])
        if disable_emittance:
            lat_fields -= {"emittance_x", "emittance_y"}
        for field in lat_fields:
            # Ignore basic devices as they do not have PVs.
            if not isinstance(self.lattice.get_device(field), SimpleDevice):
                get_pv = self.lattice.get_pv_name(field, pytac.RB)
                value = self.lattice.get_value(
                    field, units=pytac.ENG, data_source=pytac.SIM
                )
                builder.SetDeviceName(get_pv.split(":", 1)[0])
                in_record = builder.aIn(
                    get_pv.split(":", 1)[1], PREC=4, initial_value=value, MDEL="-1"
                )
                self._in_records[in_record] = ([0], field)
                self._rb_only_records.append(in_record)
        self._update_record_names(
            list(self._in_records.keys()) + list(self._out_records.keys())
        )
        print("~*~*Woah, we're halfway there, Wo-oah...*~*~")

    def _on_update(self, value, name):
        """The callback function passed to out records, it is called after
        successful record processing has been completed. It updates the out
        record's corresponding in record with the value that has been set and
        then sets the value to the Pytac lattice.

        This functions needs to be kept FAST as it can be called rapidly by CA clients.

        Args:
            value (number): The value that has just been set to the record.
            name (str): The name of record object that has just been set to.
        """
        logging.debug("Read value %s on pv %s", value, name)
        in_record = self._out_records[self._record_names[name]]
        in_record.set(value)
        index, field = self._in_records[in_record]
        if self.tune_feedback_status is True:
            try:
                offset_record = self._offset_pvs[name]
                value += offset_record.get()
            except KeyError:
                pass

        for i in index:
            self.lattice[i - 1].set_value(
                field, value, units=pytac.ENG, data_source=pytac.SIM
            )

    def _create_bba_records(self, bba_csv):
        """Create all the beam-based-alignment records from the .csv file at the
        location passed, see create_csv.py for more information.

        Args:
            bba_csv (str): The filepath to the .csv file to load the
                                    records in accordance with.
        """
        self._bba_records = self._create_feedback_or_bba_records_from_csv(bba_csv)
        self._update_record_names(self._bba_records.values())

    def _create_feedback_records(self, feedback_csv, disable_emittance):
        """Create all the feedback records from the .csv file at the location
        passed, see create_csv.py for more information; records for one edge
        case are also created.

        Args:
            feedback_csv (str): The filepath to the .csv file to load the
                                    records in accordance with.
            disable_emittance (bool): Whether the emittance related PVs should be
                                        created or not.
        """
        # Create standard records from csv
        self._feedback_records = self._create_feedback_or_bba_records_from_csv(
            feedback_csv
        )

        # We can choose to not calculate emittance as it is not always required,
        # which decreases computation time.
        if not disable_emittance:
            # Special case: EMIT STATUS for the vertical emittance feedback, since
            # we cannot currently create mbbIn records via CSV.
            builder.SetDeviceName("SR-DI-EMIT-01")
            emit_status_record = builder.mbbIn(
                "STATUS", initial_value=0, ZRVL=0, ZRST="Successful", PINI="YES"
            )
            self._feedback_records[(0, "emittance_status")] = emit_status_record

        self._update_record_names(self._feedback_records.values())

    def _create_feedback_or_bba_records_from_csv(
        self, csv_file
    ) -> dict[tuple[int, str], typing.Any]:
        """Read the csv file and create the corresponding records based on
        its contents.

        Args:
            csv_file (str): The filepath to the .csv file to load the
                                    records in accordance with.
        Returns:
            records dict[tuple[int, str], typing.Any]: A dictionary containing
                a tuple of indexes,field as its key and a softioc.builder record
                as its value
        """
        # We don't set limits or precision but this shouldn't be an issue as these
        # records aren't really intended to be set to by a user.
        with open(csv_file) as f:
            csv_reader = csv.DictReader(f)
            records: dict[
                tuple[int, str], builder.aIn | builder.aOut | builder.WaveformOut
            ] = {}
            for line in csv_reader:
                val: typing.Any = 0
                prefix, suffix = line["pv"].split(":", 1)
                builder.SetDeviceName(prefix)
                try:
                    # Waveform records may have values stored as a list such as: [5 1 3]
                    # Here we convert that into a numpy array for initialising the
                    # record
                    if (line["value"][0], line["value"][-1]) == ("[", "]"):
                        val = numpy.fromstring((line["value"])[1:-1], sep=" ")
                    else:
                        val = float(line["value"])
                except (AssertionError, ValueError) as exc:
                    raise ValueError(
                        f"Invalid initial value for {line['record_type']} record: "
                        f"{line['value']}"
                    ) from exc
                else:
                    if line["record_type"] == "ai":
                        record = builder.aIn(suffix, initial_value=val, MDEL="-1")
                        records[(int(line["index"]), line["field"])] = record
                    elif line["record_type"] == "ao":
                        record = builder.aOut(
                            suffix, initial_value=val, always_update=True
                        )
                        records[(int(line["index"]), line["field"])] = record
                    elif line["record_type"] == "wfm":
                        record = builder.WaveformOut(
                            suffix,
                            # We remove the [] around the string
                            initial_value=val,
                            always_update=True,
                        )
                        records[(int(line["index"]), line["field"])] = record
                    else:
                        raise ValueError(
                            f"Failed to create PV from csv file line num "
                            f"{csv_reader.line_num} invalid record_type: "
                            f"{line['record_type']}"
                        )
        return records

    def _create_mirror_records(self, mirror_csv):
        """Create all the mirror records from the .csv file at the location
        passed, see create_csv.py for more information.

        Args:
            mirror_csv (str): The filepath to the .csv file to load the
                                    records in accordance with.
        """
        with open(mirror_csv) as f:
            csv_reader = csv.DictReader(f)
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
                        "collation and summation mirror types take at least two input "
                        "PVs."
                    )
                monitor = input_pvs  # need to update to support camonitor multiple
                # Convert input pvs to record objects
                input_records = []
                for pv in input_pvs:
                    try:
                        input_records.append(self._record_names[pv])
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
                    output_record = builder.longIn(
                        suffix, initial_value=value, MDEL="-1"
                    )
                elif line["output type"] == "Waveform":
                    value = numpy.asarray(line["value"][1:-1].split(", "), dtype=float)
                    output_record = builder.Waveform(suffix, initial_value=value)
                else:
                    raise TypeError(
                        f"{line['output type']} isn't a supported mirroring output "
                        "type; please enter 'caput', 'aIn', 'longIn', or 'Waveform'."
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
                        f"{line['mirror type']} is not a valid mirror type; please "
                        "enter a currently supported type from: 'basic', 'summate', "
                        "'collate', 'inverse', and 'refresh'."
                    )
            mirrored_records = []
            for rec_list in self._mirrored_records.values():
                for record in rec_list:
                    mirrored_records.append(record)
        self._update_record_names(mirrored_records)

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
                warn(e, stacklevel=1)

    def refresh_record(self, pv_name):
        """For a given PV refresh the time-stamp of the associated record,
        this is done by setting the record to its current value.

        Args:
            pv_name (str): The name of the record to refresh.
        """
        try:
            record = self._record_names[pv_name]
        except KeyError as exc:
            raise ValueError(
                f"{pv_name} is not the name of a record created by this server."
            ) from exc
        else:
            record.set(record.get())

    def setup_tune_feedback(self, tune_csv=None):
        """Read the tune feedback .csv and find the associated offset PVs,
        before starting monitoring them for a change to mimic the behaviour of
        the quadrupoles used by the tune feedback system on the live machine.

        .. Note:: This is intended to be on the recieving end of the tune
           feedback system and doesn't actually perfom tune feedback itself.

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
        with open(self._tune_fb_csv_path) as f:
            csv_reader = csv.DictReader(f)
            if not self._pv_monitoring:
                self.monitor_mirrored_pvs()
            self.tune_feedback_status = True
            for line in csv_reader:
                offset_record = self._record_names[line["offset"]]
                self._offset_pvs[line["set pv"]] = offset_record
                mask = callback_offset(self, line["set pv"], offset_record)
                try:
                    self._monitored_pvs[line["delta"]] = camonitor(
                        line["delta"], mask.callback
                    )
                except Exception as e:
                    warn(e, stacklevel=1)

    def stop_all_monitoring(self):
        """Stop monitoring mirrored records and tune feedback offsets."""
        for subscription in self._monitored_pvs.values():
            subscription.close()
        self.tune_feedback_status = False
        self._pv_monitoring = False

    def set_feedback_record(self, index, field, value):
        """Set a value to the feedback in records.

        possible element fields are:
            ['error_sum', 'enabled', 'state', 'offset', 'golden_offset', 'bcd_offset',
             'bba_offset']
        possible lattice fields are:
            ['beam_current', 'feedback_status', 'bpm_id', 'emittance_status',
             'fofb_status', 'cell_<cell_number>_excite_start_times',
             'cell_<cell_number>_excite_amps', 'cell_<cell_number>_excite_deltas',
             'cell_<cell_number>_excite_ticks', 'cell_<cell_number>_excite_prime']

        Args:
            index (int): The index of the element on which to set the value;
                          starting from 1, 0 is used to set on the lattice.
            field (str): The field to set the value to.
            value (number): The value to be set.

        Raises:
            pytac.FieldException: If the lattice or element does
                                              not have the specified field.
        """
        try:
            self._feedback_records[(index, field)].set(value)
            self._bba_records[(index, field)].set(value)
        except KeyError as exc:
            if index == 0:
                raise FieldException(
                    f"Simulated lattice {self.lattice} does not have field {field}."
                ) from exc
            else:
                raise FieldException(
                    f"Simulated element {self.lattice[index]} does not have "
                    f"field {field}."
                ) from exc
