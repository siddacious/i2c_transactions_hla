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
    register_address: int
    register_name: str
    _last_addr_frame: int
    data: bytearray

    def __init__(self, start_time):
        self.start_time = start_time
        self.is_multibyte_read = False
        self.end_time = None
        self.register_address = None
        self.register_name = ""
        self._last_addr_frame = None
        self.data = bytearray()

    @property
    def last_address_frame(self):
        """The last address frame sent by the I2C master to set the target slave
        and declare if the following frames will be written or read by the master"""
        return self._last_addr_frame

    @last_address_frame.setter
    def last_address_frame(self, frame):
        self._last_addr_frame = frame

    @property
    def i2c_node_addr(self):
        """The 7-bit I2C slave address of the target device, derived from the last address frame"""
        return (self._last_addr_frame & 0x7E)>>1

    @property
    def is_read(self):
        """True if the transaction is a read, False if it is a write. Derived from the last
        address frame before a STOP frame as the initial address frame will always be a write"""
        return (self._last_addr_frame & 1) > 0

    def __str__(self):
        out_str = ""
        if self.last_address_frame:
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

        self._load_register_map()
        self.decoder = RegisterDecoder(register_map=self.register_map)


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
            map_loader = CSVRegisterMapLoader(self.register_map_file)

        elif self.register_map_file.endswith(".json"):
            from json_loader import JSONRegisterMapLoader
            map_loader = JSONRegisterMapLoader(self.register_map_file)
        else:
            raise AttributeError("Provided register map does not have a supported extension: [json, csv]"%)

        if map_loader.map is None :
            raise AttributeError("Register MapLoader could not load a map")
        self.register_map = map_loader.map

    def process_transaction(self):
        txn = self.current_transaction
        address_byte = txn.data.pop(0)
        # if self.mode == MODE_AUTO_INCREMENT_ADDR_MSB_HIGH:
        #     address_byte &= 0x7F # clear any MSB used for auto increment

        ############ register naming #####################

        address_key = str(address_byte)
        if address_key in self.current_map.keys():
            register_name = self.current_map[address_key]['name']
        else:
            # TODO: WRITE UNKNOWN DOES NOT DISPLAY CORRECTLY, READ UNKNOWN DOES
            register_name = "UNKNOWN[%s]"%hex(address_byte)

        txn.register_name = register_name
        txn.register_address = address_byte
        # transaction_string = self.decoder.decode(self.current_transaction)

        ###################################################
        transaction_string = str(txn)
        print(transaction_string)
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
        byte = frame.data['data'][0]


        self.current_transaction.data.append(byte)

    def _process_address_frame(self, frame):
        address_frame_data = frame.data['address'][0]
        self.current_transaction.last_address_frame = address_frame_data

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

                # def set_settings(self, settings):
    #     '''
    #     Handle the settings values chosen by the user, and return information about how to display the results that `decode` will return.

    #     This method will be called second, after `get_capbilities` and before `decode`.
    #     '''
    #     if 'Register map (json)' in settings and settings['Register map (json)']:
    #         self.register_map_file = settings['Register map (json)']
    #         print("File is '%s'"%self.register_map_file)
    #     else:
    #         print("No register map provided...", end="")
    #         self.register_map_file = '/Users/bs/dev/logic_hlas/i2c_txns/register_map_v1.json'
    #     self._load_register_map()

    #     if 'Multi-byte auto-increment mode' in settings:
    #         mode_setting = settings['Multi-byte auto-increment mode']
    #         if mode_setting == 'MODE_AUTO_INCREMENT_DEFAULT':
    #             self.mode = MODE_AUTO_INCREMENT_DEFAULT
    #         elif mode_setting == 'MODE_AUTO_INCREMENT_DEFAULT':
    #             self.mode = MODE_AUTO_INCREMENT_DEFAULT

    #     if 'Debug Print' in settings:
    #         print("debug in settings:", settings['Debug Print'])
    #         self._debug = settings['Debug Print'] == 'True'
    #         print("self._debug:", self._debug)

    #     return {
    #         'result_types': {
    #             'i2c_frame  ': {
    #                 'format': '{{data.out_str}}'
    #             },
    #             'transaction': {
    #                 'format': '{{data.transaction_string}}'
    #             }
    #         }
    #     }