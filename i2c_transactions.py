import os
import json
from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, StringSetting, NumberSetting, ChoicesSetting
from register_decoder import RegisterDecoder
import csv_loader
# import json_loader
# https://support.saleae.com/extensions/analyzer-frame-types


class Transaction:
    """A class representing a complete read or write transaction between an I2C Master and a slave device with addressable registers"""
    end_time: float
    #is_multibyte_read: bool
    is_write: bool
    start_time: float
    _last_addr_frame: int
    data: bytearray
    register_address: int

    def __init__(self, start_time):
        self.start_time = start_time
        self.end_time = None
        self.register_address = None
        self.data = bytearray()
        self.write = True 

        # we would know this if prev start was a read and len(data) >1
        # this means it is likely reading from a data register, right? Unless registers are muilti-byte (config). This would matter if reads were auto incrementing and we
        # were reading multiple data registers simultaneously
        #self.is_multibyte_read = False

    def __str__(self):
        out_str = ""
        if self.write:
            out_str +="WRITE"
        else:
            out_str +="READ"
        if self.register_address:
            out_str +=" RegAddr: 0x{:02X}".format(self.register_address)
        if len(self.data) > 0:
            byte_list = ["0x{:02X}".format(i) for i in self.data]
            byte_list_str = ", ".join(byte_list)
            out_str +=" Bytes: [%s]"%(byte_list_str)
        return out_str

class I2CRegisterTransactions(HighLevelAnalyzer):
    # json_register_map_path = StringSetting(label='Register map (JSON)')
    # csv_register_map_path = StringSetting(label='Register map (CSV)')
    pickled_register_map_path = StringSetting(label='Register map (Python Pickle)')

#    # List of settings that a user can set for this High Level Analyzer.
#     my_string_setting = StringSetting()
#     my_number_setting = NumberSetting(min_value=0, max_value=100)
#     my_choices_setting = ChoicesSetting(choices=('A', 'B'))

    # TODO: consider other frame types
    result_types = {
        'i2c_frame  ': {
            'format': '{{data.out_str}}'
        },
        'transaction': {
            'format': '{{data.transaction_string}}'
        }
    }

    def __init__(self):
        '''
        Initialize this HLA.

        If you have any initialization to do before any methods are called, you can do it here.
        '''
        self.current_frame = None
        self.current_transaction = None
        self.address_is_write = False
        #self.register_map = None
        # self.decoder = RegisterDecoder(register_map=self.register_map)
        self.decoder = None

        self._init_decoder()
        if not self.decoder:
            raise  AttributeError("You must provide a path to a valid register map")


    def _init_decoder(self):
        if self.pickled_register_map_path and os.path.exists(self.pickled_register_map_path):
            self.decoder = RegisterDecoder(pickled_map_path=self.pickled_register_map_path)
        # CSV support here

    def process_transaction(self):
        # This doesn't need to be in here?
        self.current_transaction.register_address = self.current_transaction.data.pop(0)
        # we can also set the type here
        transaction_string = self.decoder.decode_transaction(self.current_transaction)

        new_frame = {
            'type': 'transaction',
            'start_time': self.current_transaction.start_time,
            'end_time': self.current_transaction.end_time,
            'data': {
                'transaction_string' : transaction_string
            }
        }
        new_frame = AnalyzerFrame('transaction',
            self.current_transaction.start_time, self.current_transaction.end_time, {
            'input_type': self.current_frame.type, 'transaction_string':transaction_string
        })

        return new_frame

    def _process_address_frame(self, frame):
        self.address_is_write = not frame.data['read']

    def _process_data_frame(self, frame):
        byte = int.from_bytes(frame.data['data'], 'little')

        self.current_transaction.data.append(byte)

    def _process_stop_frame(self, frame):
        # we don't want to end on the stop after a single byte write
        # which is used to set up a read.
        # we _do_ want to save that data as the register address that is being read from
        # so! if the current transaction's data is len(1) and the previous address frame
        # was for a write, pop the byte off the bytes collection and use it to set
        # the current transaction's register address

        # otherwise, we are ending a
        # * multi-byte write (reg addr+ values)
        #   - in this case, the register address is the first byte of the data
        # * single or multi-byte read ( read data)
        #   - reg address was previous set by the write used to set the read up
        # in either case the transaction frame should be ended and returned.
        # REVISED!
        # in either case (read or write), all the data frames are used and the first
        # will always be the register address!
        # This means the only difference is that reads transactions do not process the first write, but they still append their data

        if self.address_is_write and len(self.current_transaction.data) == 1:
            # do nothing?
            return
        # setting the end time will trigger processing the txn
        self.current_transaction.end_time = frame.end_time


        return

    def decode(self, frame):
        self.current_frame = frame
        new_frame = None
        frame_type = frame.type


        if frame_type == 'start': # begin new transaction or repeated start
            if self.current_transaction is None:
                self.current_transaction = Transaction(start_time=frame.start_time)
        if self.current_transaction is None:
            return

        if frame_type == 'address': # read or write + I2C slave addr
            self._process_address_frame(frame)
        if frame_type == 'data': # register address and data
            self._process_data_frame(frame)

        if frame_type == 'stop': # transaction end, ready to process
            self._process_stop_frame(frame)

        if self.current_transaction.end_time:

            # in the rack-like model we would just pass the txn and other rack item would process it
            transaction_frame = self.process_transaction()
            # expecting start to create a new txn?
            # should be created after start frame is processed
            # which will set...??? frame start 
            self.current_transaction = None
            return transaction_frame


