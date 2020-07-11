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
    is_multibyte_read: bool
    is_read: bool
    start_time: float
    register_name: str
    _last_addr_frame: int
    data: bytearray
    i2c_node_addr: int
    register_address: int

    def __init__(self, start_time):
        self.start_time = start_time
        self.is_multibyte_read = False
        self.end_time = None
        self.register_address = None
        self.register_name = ""
        self.data = bytearray()
        self._read = False
        self._i2c_node_addr = 0xFF


    @property
    def i2c_node_addr(self):
        """The 7-bit I2C slave address of the target device, derived from the last address frame"""
        return (self._i2c_node_addr)
    @i2c_node_addr.setter
    def i2c_node_addr(self, value):
        self._i2c_node_addr = value
    @property
    def is_read(self):
        """True if the transaction is a read, False if it is a write. Derived from the last
        address frame before a STOP frame as the initial address frame will always be a write"""
        return (self._read)
    @is_read.setter
    def is_read(self, value):
        self._read = value


    def __str__(self):
        out_str = ""
        if self.is_read:
            out_str +=" READ"
        else:
            out_str +=" WRITE"
            # TODO: option to show slave addr
            # out_str +=" (%s)"%hex(self.i2c_node_addr)
        if self.register_name and self.register_address:
            out_str += " %s"%self.register_name
            out_str += " (%s)"%hex(self.register_address)
        if len(self.data) > 0:
            byte_list = [hex(i) for i in self.data]
            byte_list_str = ", ".join(byte_list)
            out_str +=" Bytes: [%s]"%(byte_list_str)
        return out_str

MODE_AUTO_INCREMENT_ADDR_MSB_HIGH = 0
MODE_AUTO_INCREMENT_DEFAULT = 1

class I2CRegisterTransactions(HighLevelAnalyzer):
#    # List of settings that a user can set for this High Level Analyzer.
#     my_string_setting = StringSetting()
#     my_number_setting = NumberSetting(min_value=0, max_value=100)
#     my_choices_setting = ChoicesSetting(choices=('A', 'B'))

#     class MyHla(HighLevelAnalyzer):
#     my_string_setting = StringSetting(label='Register map (JSON)')
#     my_number_setting = NumberSetting(label='My Number', min_value=0, max_value=100)
#     my_choices_setting = ChoicesSetting(label='My Choice', ['A', 'B'])


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
        self.prev_frame = None
        self.current_frame = None
        self.current_transaction = None
        self._debug = False

        self.mode = MODE_AUTO_INCREMENT_DEFAULT

        self.register_map = None
        self.register_map_file = None
        self.current_bank = 0
        self.current_map = {}
        # take from setting
        self.register_map_file = '/Users/bs/dev/tooling/i2c_txns/maps/as7341_map.csv'

        # self._load_register_map()
        # self.decoder = RegisterDecoder(register_map=self.register_map)
        self.decoder = RegisterDecoder()


    def get_capabilities(self):
        '''
        Return the settings that a user can set for this High Level Analyzer. The settings that a user selects will later be passed into `set_settings`.

        This method will be called first, before `set_settings` and `decode`
        '''

        return {
            'settings': {
                'Register map (json)': {
                    'type': 'string',
                },
                'Multi-byte auto-increment mode': {
                    'type': 'choices',
                    'choices': ('MODE_AUTO_INCREMENT_DEFAULT', 'MODE_AUTO_INCREMENT_ADDR_MSB_HIGH')
                },
                'Debug Print': {
                    'type': 'choices',
                    'choices': ('False', 'True')
                }
            }
        }

    def _load_register_map(self):
        if not os.path.exists(self.register_map_file):
            raise FileNotFoundError("no register map found at %s"%self.register_map_file)


        print("loading register map from %s"%self.register_map_file)
        if self.register_map_file.endswith(".csv"):
            from csv_loader import CSVRegisterMapLoader
            map_loader = CSVRegisterMapLoader([self.register_map_file])

        elif self.register_map_file.endswith(".json"):
            from json_loader import JSONRegisterMapLoader
            map_loader = JSONRegisterMapLoader(self.register_map_file)
        else:
            raise AttributeError("Provided register map %s does not have a supported extension: [json, csv]"%self.register_map_file)

        if map_loader.map is None:
            raise AttributeError("Register MapLoader could not load a map")
        self.register_map = map_loader.map

    def process_transaction(self):
        print(self.current_transaction)
        transaction_string = self.decoder.decode_transaction(self.current_transaction)

        ###################################################
        # transaction_string = str(txn)
        print("DECODED:", transaction_string)
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

    def _process_data_frame(self, frame):
        byte = int.from_bytes(frame.data['data'], 'little')


        self.current_transaction.data.append(byte)

    def _process_address_frame(self, frame):
        address= frame.data['address'] # bytes
        read = frame.data['read'] # bool
        ack = frame.data['ack'] # bool

        self.current_transaction.is_read = read
        self.current_transaction.i2c_node_addr = address
    def _process_start_frame(self, frame):
        if self.current_transaction: # repeated start
            return
        self.current_transaction = Transaction(frame.start_time)

    def _process_stop_frame(self, frame):
        self.current_transaction.end_time = frame.end_time
        new_frame = self.process_transaction()
        self.current_transaction = None

        return new_frame

    def decode(self, frame):
        self.current_frame = frame
        new_frame = None
        frame_type = frame.type

        if self._debug: print(frame_type.upper())

        if frame_type == 'start': # begin new transaction or repeated start
            self._process_start_frame(frame)
        if self.current_transaction is None:
            if self._debug: print("EXITing `decode` due to missing transaction for non-start frame")
            return

        if frame_type == 'address': # read or write + I2C slave addr
            self._process_address_frame(frame)
        elif frame_type == 'data': # register address and data
            self._process_data_frame(frame)

        elif frame_type == 'stop': # transaction end, ready to process
            new_frame = self._process_stop_frame(frame)

        self.prev_frame = frame

        if new_frame:
            if self._debug:
                print("\nNEW_FRAME:")
                for key, value in new_frame.items():
                        print(key, "=>", value)

            return new_frame

        # return AnalyzerFrame('mytype', frame.start_time, frame.end_time, {
        #     'input_type': frame.type
        # })

        if self.current_transaction and self._debug:

            print(self.current_transaction)

  