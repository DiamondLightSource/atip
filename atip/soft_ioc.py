import csv
from softioc import builder, softioc
import pytac
from pytac.exceptions import FieldException

class soft_ioc(object):
    def __init__(self, lattice, feedback_pvs):
        self.lattice = lattice
        self.in_records = {}
        self.out_records = {}
        self.RB_only_records = []
        self.feedback_records = {}
        self.create_records()
        self.create_feedback_records(feedback_pvs)
        # add special case out record for SOFB to write to
        builder.aOut('CS-CS-MSTAT-01:FBHEART', initial_value=10)
        builder.LoadDatabase()
        softioc.iocInit()

    def create_records(self):
        # {in_records: [index, field]}
        # {out_records: in_record}
        for element in self.lattice:
            for field in element.get_fields()[pytac.SIM]:
                value = element.get_value(field, data_source=pytac.SIM)
                get_pv = element.get_pv_name(field, pytac.RB)
                in_record = builder.aIn(get_pv, initial_value=value)
                self.in_records[in_record] = (element.index, field)
                try:
                    set_pv = element.get_pv_name(field, pytac.SP)
                    out_record = builder.aOut(set_pv, initial_value=value,
                                              validate=self.validate)
                    self.out_records[out_record] = in_record
                except FieldException:
                    self.RB_only_records.append(in_record)
        lat_fields = self.lattice.get_fields()
        for field in set(lat_fields[pytac.LIVE]) & set(lat_fields[pytac.SIM]):
            value = lattice.get_value(field, data_source=pytac.SIM)
            in_record = builder.aIn(lattice.get_pv_name(field, pytac.RB),
                                    initial_value=value)
            self.in_records[in_record] = (0, field)
            self.RB_only_records.append(in_record)

    def create_feeback_records(self, feedback_pvs):
        csv_reader = csv.DictReader(open(feedback_pvs))
        for line in csv_reader:
            in_record = builder.longIn(line['pv'], initial_value=line['value'])
            self.feedback_records[(line['id'], line['field'])] = in_record

    def validate(self, record, value):
        index, field = self.in_records[self.out_records[record]]
        self.lattice[index-1].set_value(field, value, data_source=pytac.SIM)
        in_record = self.out_records[record]
        in_record.set(value)

    def update(self):
        for RB_record in self.RB_only_records:
            index, field = self.in_records[RB_record]
            if index is 0:
                RB_record.set(lattice.get_value(field, data_source=pytac.SIM)
            else:
                RB_record.set(lattice[index-1].get_value(field,
                                                         data_source=pytac.SIM)

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
