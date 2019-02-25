import csv
from softioc import builder, softioc
import pytac
from pytac.exceptions import HandleException, DataSourceException


class ATIPServer(object):
    def __init__(self, lattice, feedback_csv):
        self.lattice = lattice
        self.in_records = {}
        self.out_records = {}
        self.rb_only_records = []
        self.feedback_records = {}
        self.create_records()
        self.create_feedback_records(feedback_csv)

    def create_records(self):
        # {in_records: [index, field]}
        # {out_records: in_record}
        bend_set = False
        for element in self.lattice:
            if element.type_ == 'BEND':
                if not bend_set:
                    # Get bends only once as they all share a single PV.
                    value = element.get_value('b0', units=pytac.ENG,
                                              data_source=pytac.SIM)
                    get_pv = element.get_pv_name('b0', pytac.RB).split(':', 1)
                    builder.SetDeviceName(get_pv[0])
                    in_record = builder.aIn(get_pv[1], initial_value=value)
                    set_pv = element.get_pv_name('b0', pytac.SP).split(':', 1)
                    builder.SetDeviceName(set_pv[0])
                    out_record = builder.aOut(set_pv[1], initial_value=value,
                                              validate=self.validate)
                self.in_records[in_record] = (element.index, 'b0')
                self.out_records[out_record] = in_record
                bend_set = True
            else:
                for field in element.get_fields()[pytac.SIM]:
                    value = element.get_value(field, units=pytac.ENG,
                                              data_source=pytac.SIM)
                    get_pv = element.get_pv_name(field, pytac.RB).split(':', 1)
                    builder.SetDeviceName(get_pv[0])
                    in_record = builder.aIn(get_pv[1], initial_value=value)
                    self.in_records[in_record] = (element.index, field)
                    try:
                        set_pv = element.get_pv_name(field,
                                                     pytac.SP).split(':', 1)
                    except HandleException:
                        self.rb_only_records.append(in_record)
                    else:
                        builder.SetDeviceName(set_pv[0])
                        out_record = builder.aOut(set_pv[1],
                                                  initial_value=value,
                                                  validate=self.validate)
                        self.out_records[out_record._RecordWrapper__device] = in_record
        # Now for lattice fields
        lat_fields = self.lattice.get_fields()
        for field in set(lat_fields[pytac.LIVE]) & set(lat_fields[pytac.SIM]):
            try:
                get_pv = self.lattice.get_pv_name(field,
                                                  pytac.RB).split(':', 1)
            except DataSourceException:
                pass  # Ignore basic devices
            else:
                value = self.lattice.get_value(field, units=pytac.ENG,
                                               data_source=pytac.SIM)
                builder.SetDeviceName(get_pv[0])
                in_record = builder.aIn(get_pv[1], initial_value=value)
                self.in_records[in_record] = (0, field)
                self.rb_only_records.append(in_record)

    def create_feedback_records(self, feedback_csv):
        csv_reader = csv.DictReader(open(feedback_csv))
        for line in csv_reader:
            prefix, pv = line['pv'].split(':', 1)
            builder.SetDeviceName(prefix)
            in_record = builder.longIn(pv, initial_value=int(line['value']))
            self.feedback_records[(line['id'], line['field'])] = in_record

    def validate(self, record, value):
        in_record = self.out_records[record]
        index, field = self.in_records[in_record]
        self.lattice[index - 1].set_value(field, value, units=pytac.ENG,
                                          data_source=pytac.SIM)
        in_record.set(value)
        for rb_record in self.rb_only_records:
            index, field = self.in_records[rb_record]
            if index is 0:
                rb_record.set(self.lattice.get_value(field, units=pytac.ENG,
                                                     data_source=pytac.SIM))
            else:
                element = self.lattice[index - 1]
                rb_record.set(element.get_value(field, units=pytac.ENG,
                                                data_source=pytac.SIM))
        return True

    def set_feeback_pvs(self, index, field, value):
        # ['x_fofb_disabled', 'x_sofb_disabled', 'error_sum',
        #  'y_fofb_disabled', 'y_sofb_disabled', 'enabled',
        #  'h_fofb_disabled', 'h_sofb_disabled', 'state',
        #  'v_fofb_disabled', 'v_sofb_disabled']
        try:
            self.feedback_records[(index, field)].set(value)
        except KeyError:
            if index is 0:
                raise FieldException("Lattice {0} does not have field {1}."
                                     .format(self.lattice, field))
            else:
                raise FieldException("Element {0} does not have field {1}."
                                     .format(self.lattice[index], field))
