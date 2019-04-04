import csv

import pytac
from pytac.device import BasicDevice
from pytac.exceptions import HandleException, FieldException
from softioc import builder


class ATIPServer(object):
    """A soft-ioc server allowing ATIP to be interfaced using EPICS, in the
    same manner as the live machine.

    **Attributes**

    Attributes:
        lattice (pytac.lattice.Lattice): An instance of a pytac lattice with a
                                          simulator data source.
    .. Private Attributes:
           _in_records (dict): A dictionary containing all the created in
                                records and their associated element index and
                                pytac field, i.e. {in_record: [index, field]}.
           _out_records (dict): A dictionary containing all the created out
                                 records and their associated in records, i.e.
                                 {out_record: in_record}.
           _rb_only_records (list): A list of all the in records that do not
                                     have an associated out record.
           _feedback_records  (dict): A dictionary containing all the feedback
                                       related records, in the same format as
                                       _in_records because they are all
                                       readback only.
    """
    def __init__(self, lattice, pv_limits, feedback_csv):
        """
        Args:
            lattice (pytac.lattice.Lattice): An instance of a pytac lattice
                                              with a simulator data source.
            feedback_csv (string): The filepath to the .csv file from which to
                                    load the feedback records, for more
                                    information see create_feedback_csv.py.
        """
        self.lattice = lattice
        self._in_records = {}
        self._out_records = {}
        self._rb_only_records = []
        self._feedback_records = {}
        self._create_records(pv_limits)
        self._create_feedback_records(feedback_csv)

    @property
    def total_records(self):
        return sum([len(self._in_records), len(self._out_records),
                    len(self._feedback_records)])

    def _create_records(self, pv_limits):
        """Create all the standard records from both lattice and element pytac
        fields. Several assumptions have been made for simplicity and
        efficiency, these are:
            - That bend elements all share a single PV, and are the only
               family to do so.
            - That every field that has an out record (SP) will also have an in
               record (RB).
            - That all lattice fields are never setpoint and so only in records
               need to be created for them.
        """
        limits_dict = {}
        csv_reader = csv.DictReader(open(pv_limits))
        for line in csv_reader:
            limits_dict[line['pv']] = (float(line['upper']),
                                       float(line['lower']))
        print("Starting record creation.")
        bend_set = False
        for element in self.lattice:
            if element.type_ == 'BEND':
                # Create bends only once as they all share a single PV.
                if not bend_set:
                    value = element.get_value('b0', units=pytac.ENG,
                                              data_source=pytac.SIM)
                    get_pv = element.get_pv_name('b0', pytac.RB).split(':', 1)
                    upper, lower = limits_dict[get_pv[0] + ':' + get_pv[1]]
                    builder.SetDeviceName(get_pv[0])
                    in_record = builder.aIn(get_pv[1], LOPR=lower, HOPR=upper,
                                            initial_value=value)
                    set_pv = element.get_pv_name('b0', pytac.SP).split(':', 1)
                    #upper, lower = limits_dict[set_pv[0] + ':' + set_pv[1]]
                    builder.SetDeviceName(set_pv[0])
                    out_record = builder.aOut(set_pv[1], LOPR=lower,
                                              HOPR=upper, initial_value=value,
                                              validate=self._validate)
                    # how to solve the index problem?
                    self._in_records[in_record] = (element.index, 'b0')
                    wrapperless_record = out_record._RecordWrapper__device
                    self._out_records[wrapperless_record] = in_record
                    bend_set = True
            elif element.type_ in ['VTRIM', 'HTRIM', 'VSTR', 'HSTR', 'SEXT',
                                   'QUAD', 'RF']:
                # Create records for families with limits.
                for field in element.get_fields()[pytac.SIM]:
                    value = element.get_value(field, units=pytac.ENG,
                                              data_source=pytac.SIM)
                    get_pv = element.get_pv_name(field, pytac.RB).split(':', 1)
                    upper, lower = limits_dict[get_pv[0] + ':' + get_pv[1]]
                    builder.SetDeviceName(get_pv[0])
                    in_record = builder.aIn(get_pv[1], LOPR=lower, HOPR=upper,
                                            initial_value=value)
                    self._in_records[in_record] = (element.index, field)
                    try:
                        set_pv = element.get_pv_name(field,
                                                     pytac.SP).split(':', 1)
                    except HandleException:
                        self._rb_only_records.append(in_record)
                    else:
                        #upper, lower = limits_dict[set_pv[0] + ':' + set_pv[1]]
                        builder.SetDeviceName(set_pv[0])
                        out_record = builder.aOut(set_pv[1], LOPR=lower,
                                                  HOPR=upper,
                                                  initial_value=value,
                                                  validate=self._validate)
                        wrapperless_record = out_record._RecordWrapper__device
                        self._out_records[wrapperless_record] = in_record
            else:
                # Create records for all other families.
                for field in element.get_fields()[pytac.SIM]:
                    value = element.get_value(field, units=pytac.ENG,
                                              data_source=pytac.SIM)
                    get_pv = element.get_pv_name(field, pytac.RB).split(':', 1)
                    builder.SetDeviceName(get_pv[0])
                    in_record = builder.aIn(get_pv[1], initial_value=value)
                    self._in_records[in_record] = (element.index, field)
                    try:
                        set_pv = element.get_pv_name(field,
                                                     pytac.SP).split(':', 1)
                    except HandleException:
                        self._rb_only_records.append(in_record)
                    else:
                        builder.SetDeviceName(set_pv[0])
                        out_record = builder.aOut(set_pv[1],
                                                  initial_value=value,
                                                  validate=self._validate)
                        wrapperless_record = out_record._RecordWrapper__device
                        self._out_records[wrapperless_record] = in_record
        print("Finished creating {0} element records, now creating lattice "
              "records.".format(self.total_records))
        # Now for lattice fields
        lat_fields = self.lattice.get_fields()
        for field in set(lat_fields[pytac.LIVE]) & set(lat_fields[pytac.SIM]):
            # Ignore basic devices as they do not have PVs.
            if not isinstance(self.lattice.get_device(field), BasicDevice):
                get_pv = self.lattice.get_pv_name(field,
                                                  pytac.RB).split(':', 1)
                value = self.lattice.get_value(field, units=pytac.ENG,
                                               data_source=pytac.SIM)
                builder.SetDeviceName(get_pv[0])
                in_record = builder.aIn(get_pv[1], initial_value=value)
                self._in_records[in_record] = (0, field)
                self._rb_only_records.append(in_record)
        print("Finished lattice records, now creating feedback records.")
        print("~*~*Woah, we're halfway there, Wo-oah...*~*~")

    def _validate(self, record, value):
        """The callback function passed to out records, it is called after
        successful record processing has been completed. It updates the out
        record's corresponding in record with the value that has been set, it
        then sets the value to the centralised pytac lattice. Next it waits
        for ATIP to complete its calcuations before updating all the readback
        only records with the values from ATIP.

        Args:
            record (softioc.builder.aOut): The record object that has just
                                            been set to.
            value (number): The value that has just been set to the record.

        Returns:
            boolean: Always True since we always accept the data.
        """
        in_record = self._out_records[record]
        index, field = self._in_records[in_record]
        self.lattice[index - 1].set_value(field, value, units=pytac.ENG,
                                          data_source=pytac.SIM)
        in_record.set(value)
        sim = self.lattice._data_source_manager._data_sources[pytac.SIM]._atsim
        sim.wait_for_calculations()
        for rb_record in self._rb_only_records:
            index, field = self._in_records[rb_record]
            if index is 0:
                rb_record.set(self.lattice.get_value(field, units=pytac.ENG,
                                                     data_source=pytac.SIM))
            else:
                element = self.lattice[index - 1]
                rb_record.set(element.get_value(field, units=pytac.ENG,
                                                data_source=pytac.SIM))
        return True

    def _create_feedback_records(self, feedback_csv):
        """Create all the feedback records from the .csv file at the location
        passed, see create_feedback_csv.py for more information.

        Args:
            feedback_csv (string): The filepath to the .csv file from which to
                                    load the records.
        """
        csv_reader = csv.DictReader(open(feedback_csv))
        for line in csv_reader:
            prefix, pv = line['pv'].split(':', 1)
            builder.SetDeviceName(prefix)
            in_record = builder.longIn(pv, initial_value=int(line['value']))
            self._feedback_records[(int(line['index']),
                                    line['field'])] = in_record

        # Storage ring electron BPMs enabled
        # Special case: since cannot currently create waveform records via CSV,
        # create by hand and add to list of feedback records
        N_BPM = len(self.lattice.get_elements('BPM'))
        builder.SetDeviceName("SR-DI-EBPM-01")
        bpm_enabled_record = builder.Waveform("ENABLED", NELM=N_BPM,
                                              initial_value=[1]*N_BPM)
        self._feedback_records[(0, "bpm_enabled")] = bpm_enabled_record
        print("Finished creating all {0} records.".format(self.total_records))

    def set_feedback_record(self, index, field, value):
        """Set a value to the feedback in records, possible fields are:
            ['x_fofb_disabled', 'x_sofb_disabled', 'y_fofb_disabled',
             'y_sofb_disabled', 'h_fofb_disabled', 'h_sofb_disabled',
             'v_fofb_disabled', 'v_sofb_disabled', 'error_sum', 'enabled',
             'state', 'beam_current', feedback_status', 'bpm_enabled']

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
            if index is 0:
                raise FieldException("Lattice {0} does not have field {1}."
                                     .format(self.lattice, field))
            else:
                raise FieldException("Element {0} does not have field {1}."
                                     .format(self.lattice[index], field))
