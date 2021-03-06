#!/usr/bin/env python
import sys
import csv
import re
import itertools
from sys import argv
from os.path import exists
from pickle import load

DEBUG = 0
VERBOSE = False
ROW_NUMBER_OFFSET = 2
ROW_NUMBER_OFFSET = 2
bank0 = None
bank1 = None
BITFIELD_REGEX = '^([^\[]+)\[(\d):(\d)\]$' # matches WHO_AM_I[7:0], DISABLE_ACCEL[5:3] etc.

#self.register_map_file = '/Users/bs/dev/tooling/i2c_txns/maps/as7341_map.csv'

hardcoded_cvs = {
    "GYRO_FS_SEL" : [
        "±250 dps",
        "±500 dps",
        "±1000 dps",
        "±2000 dps"
    ],
    "GYRO_DLPFCFG":["FREQ_196_6HZ_3DB",
        "FREQ_151_8HZ_3DB",
        "FREQ_119_5HZ_3DB",
        "FREQ_51_2HZ_3DB",
        "FREQ_23_9HZ_3DB",
        "FREQ_11_6HZ_3DB",
        "FREQ_5_7HZ_3DB",
        "FREQ_361_4HZ_3DB"
        ],

    "ACCEL_FS_SEL" : ["±2 g","±4 g","±8 g","±16 g"],

    "ACCEL_DLPFCFG":[
        "FREQ_246_0HZ_3DB",
        "FREQ_111_4HZ_3DB",
        "FREQ_50_4HZ_3DB",
        "FREQ_23_9HZ_3DB",
        "FREQ_11_5HZ_3DB",
        "FREQ_5_7HZ_3DB",
        "FREQ_473HZ_3DB"
    ],
    "I2C_MST_CLK" : ["370.29 Hz", "Auto Select Best", "370.29 Hz", "432.00 Hz", "370.29 Hz", "370.29 Hz", "345.60 Hz", "345.60 Hz", "304.94 Hz", "432.00 Hz","432.00 Hz","432.00 Hz","471.27 Hz","432.00 Hz","345.60 Hz", "345.60 Hz"]

}
def debug_print(*args, **kwargs):
    if DEBUG >=3:
        print("\t\t\t\t\tDEBUG:", *args, **kwargs)

def newp(new_s, tabs=6):
    print("%s         \t%s"%("\t"*tabs, new_s))

def verbose_print(*args, **kwargs):
    if DEBUG >=3:
        print("LOG:", *args, **kwargs)

def verbose_debug(*args, **kwargs):
    if DEBUG >=3:
        verbose_print("DEBUG:", *args, **kwargs)
def pretty(d, indent=0):
    for key, value in d.items():
        print(' ' * indent + "k:"+str(key))
        if isinstance(value, dict):
            pretty(value, indent+1)
        else:
            print(' ' * (indent+1) + "↳"+str(value))

# TODO: option to print/report unchanged bitfields
# TODO: multi-byte register handling
class RegisterDecoder:

    def __init__(self, register_map=None, log_path="/Users/bs/cp/Adafruit_CircuitPython_AS7341/reg.log", pickled_map_path=None, pickled_cvs_path="/Users/bs/dev/tooling/i2c_txns/maps/as7341_cv.pickle"):
        #self.register_map = register_map
        self.register_width = 1
        self.cvs = {}
        # if not exists(log_path):
        #     with open(log_path, 'x') as f:
        #         f.write("")

        self.log_file = open("/Users/bs/cp/Adafruit_CircuitPython_AS7341/reg.log", "a")
        if register_map is None:
            if pickled_map_path:
                if exists(pickled_map_path):
                    self.register_map  = load( open( pickled_map_path, "rb" ) )
                else:
                    AttributeError("you must provide a pickled register map")
            else:
                AttributeError("you must provide a register map")
        if pickled_cvs_path:
            if exists(pickled_cvs_path):
                with open(pickled_cvs_path, 'rb') as f:
                    self.cvs = load(f)


        self.prev_single_byte_write = None
        self.current_bank = 0
        pretty(self.register_map)

    def decode(self, row_num, row):
        adjusted_row_num = row_num + ROW_NUMBER_OFFSET
        b0 = None
        b1 = None
        ############### cast fields ###########
        # check for read/write

        if not (
            "byte0" in row.keys()
            and len(row["byte0"].strip()) > 0
            and "rw" in row.keys()
            and len(row["rw"].strip()) > 0
        ):
            debug_print("SKIPPING:", "\tRow number:", row_num, "row:", row)
            return

        is_write = row["rw"] == "WRITE"

        # TODO: Add support for an arbitrary number of bytes
        # check for a first byte
        b0 = int(row["byte0"], 16)

        if is_write == "WRITE" and (b0 != 0x7F) and (not self._reg_known(b0)):
            debug_print(
                "\n\t\tBAD KEY:",
                b0,
                "(%s)" % self._h(b0),
                "self.current_bank:",
                self.current_bank,
                "RW:",
                is_write,
                "Row number:",
                adjusted_row_num,
            )
            return

        if "byte1" in row.keys() and len(row["byte1"].strip()) > 0:
            b1 = int(row["byte1"], 16)
        verbose_print("\tRow number:", row_num, "row:", row)

        ########### Decode #################
        print(self.decode_bytes(is_write, b0, b1))

    def decode_transaction(self, reg_txn):
        #if reg_txn.write: print("WRITE")
        #if not reg_txn.write: print("READ")
        reg_txn_string = ""
        try:
            reg_txn_string = self.process_register_transaction(reg_txn.register_address, reg_txn.data, reg_txn.write)
        except Exception as inst:
            print("EXCEPTION")
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args
            print(inst)
            import traceback
            track = traceback.format_exc()
            print(track)
        reg_txn_string = reg_txn_string.strip()
        if not reg_txn_string:
            reg_txn_string = self.default_txn_summary(reg_txn.register_address, reg_txn.data, reg_txn.write)

        self.log_file.write(reg_txn_string+"\n")
        self.log_file.flush()
        return reg_txn_string

    def default_txn_summary(self, register_address, data, is_write):
        if not hasattr(data, "__len__"):
            data = [data]

        if is_write:
            rw = "WRITE"
        else:
            rw = 'READ'

        data_format_str = "0x{datum:02X} 0b{datum:08b}"
        format_str = "{rw} ADDR: 0x{register_address:02X} Data: {data_str}"
        # format_str = "[NOMATCH: 0x{register_address:02X}] {rw} reg: 0x{register_address:02X} data bytes: {data_str}"

        data_str = ", ".join([data_format_str.format(datum=x) for x in data])
        txn_string = format_str.format(register_address=register_address, rw=rw, data_str=data_str)
        #print("\t"+txn_string)
        return txn_string

        # read
            # data register readings
                # single = single register
                # multi
                    # multi-byte data
                    # multiple registers
            # current value of config register to update
                # single -bits & bitfields
                # multi - thresholds, etc.
            # reset/read bit
        # write
            # single
            # changed config register
                # reset/auto changing bit within config register
                # bitfield CV
            # multi
                # multi-byte thresholds
                # wierd registers
        # result of above:
            # output format will primarily be detmined by the format
            # of the register ie: bitfields or not

            # multi-byte txns may want to look ahead/behind:
            # if current is single bitfield/byte and
            # neighbor is the same name, join
            # if diff, report current with new name

            # if self._is_bank_change(register):
            #     if is_write:
            #     self._update_bank(register, data)
            #     def _update_bank(self, register, data):
            #         reg_addr == 0x7F:
            #         self.current_bank = value_byte >> 4
            #     return

    def process_register_transaction(self, register_address, data, is_write):
        """Update register state cache and return the transaction summary for the current register state"""

        txn_string = ""
        for offset, byte in enumerate(data):
            # single byte will never have offset >0 so....stuff
            current_address = register_address+(offset*self.register_width)
            txn_string += self.process_single_byte(current_address, byte, is_write)

        return txn_string

    def process_single_byte(self, register_address, byte, is_write):
        """Process a single-byte transaction, incoming or outgoing"""

        return self.decode_by_bitfield(register_address, byte, is_write)

    def decode_bytes(self, is_write, b0=None, b1=None):

        if b1 is None: # single byte
            return self.single_byte_decode(is_write, b0)
        elif is_write:
            if b0 not in self.register_map[self.current_bank]:
                return "UNKNOWN REG: %s"%hex(b0)
            return self.decode_set_value(is_write, b0, b1)
        else:
            raise RuntimeError("Multi-byte reads not supported")
            return

    def single_byte_decode(self, is_write, b0):

        if is_write:
            current_register = self.register_map[self.current_bank][b0]
            #bitfields = self.load_bitfields(current_register)
            self.prev_single_byte_write = b0
            return "setup read from %s"%current_register['name']
        else: #READ
            if (self.prev_single_byte_write != None):

                return "%s read as %s (%s)"%(
                        self._reg_name(self.prev_single_byte_write),
                        self._b(b0),
                        self._h(b0))

                # isn't this going to do nothing because it's a local?
                self.prev_single_byte_write = None  # shouldn't be needed

    def is_set_bank_reg(self, reg_addr):
        # TODO: this should ask the register map
        if reg_addr == 0x7F:
            return true
        return False
    def set_bank(self, reg_addr, value_byte):
        # TODO: this should set a register state object
        self.current_bank = value_byte >> 4
        return
    def decode_set_value(self, is_write, reg_addr, value_byte):

        # TODO: check this by name
        # ******* SET BANK **************
        if self.set_bank_reg(reg_addr):
            return self.set_bank(reg_addr, value_byte)


        # ****IDENTIFIED WRITE TO REG W/ NEW VALUE ***
        debug_print("SET %s to %s (%s)" % (self._reg_name(reg_addr),  self._b(value_byte), self._h(value_byte)))

        return self.decode_by_bitfield(reg_addr, value_byte, is_write)

    # TODO: this all needs to be reworked to use a register state object and register objects (or namedtuples)
    # we don't care about incoming data nearly as much as outgoing data send by the library/driver
    def decode_by_bitfield(self, register_address, new_value, is_write):

        if not self._reg_known(register_address):
            return self.default_txn_summary(register_address, new_value, is_write)
        prev_key = 'last_write'
        current_key = 'last_read'
        old_value = 0

        rw = "r "
        if is_write:
            rw = "w "
            prev_key = 'last_read'
            current_key = 'last_write'
        if not is_write:
            return "r"
        if prev_key in self.register_map[self.current_bank][register_address]:
            old_value = self.register_map[self.current_bank][register_address][prev_key]

        bitfields = self.load_bitfields(self.register_map[self.current_bank][register_address])

        ch_str = rw+self.bitfield_changes_str(old_value, new_value, bitfields)
        self.register_map[self.current_bank][register_address][current_key] = new_value

        return ch_str

    def bitfield_changes_str(self, old_value, new_value, bitfields):
        unset_bitmask, set_bitmask = self.bitwise_diff(old_value, new_value)
        changes_str = ""
        for bitfield in bitfields:
            bf_change_str = self.bitfield_change_str(bitfield, unset_bitmask, set_bitmask, new_value)
            if bf_change_str:
                print(bf_change_str)
                changes_str += bf_change_str+"\n"

        return changes_str

    def bitfield_change_str(self, bitfield, unset_bitmask, set_bitmask, new_value):

        bf_name, bf_mask, bf_shift = bitfield
        bf_value = (bf_mask & new_value) >> bf_shift

        bf_set = (bf_mask & set_bitmask) >0
        bf_unset = (bf_mask & unset_bitmask) > 0
        byte_changed = (unset_bitmask > 0) or (set_bitmask > 0)
        change_str = None
        if byte_changed and ( not (bf_set or bf_unset)):
            return change_str
        bf_cv = None

        if bf_name in self.cvs:
            bf_cv = self.cvs[bf_name]
            try:
                bf_value = bf_cv[bf_value]
            except KeyError as e:
                print(bf_name, "has no key: %s"%bf_value)
                pretty(bf_cv)
                bf_value = self._h(bf_value)

        else:
            bf_value = self._h(bf_value)
        change_str = "%s : %s"%(bf_name, bf_value)
        return change_str

    # TODO: make a bf object or namedtuple
    def load_bitfields(self, current_register):
        if 'bitfields' not in current_register:
            bitfields = []
            prev_bitfield_name = None
            for idx in range(8):
                bitfield_def = current_register[idx]
                bitfield_name, bitfield_mask, bitfield_shift = self.bitfield_def_to_bitfield(bitfield_def, idx)

                if not bitfield_name or (prev_bitfield_name == bitfield_name):
                    continue

                bitfields.append((bitfield_name, bitfield_mask, bitfield_shift))
                prev_bitfield_name = bitfield_name
            current_register['bitfields'] = bitfields
        return current_register['bitfields']

    def bitfield_def_to_bitfield(self, bitfield_def, shift):
        match = re.fullmatch(BITFIELD_REGEX, bitfield_def)
        if match: #
            bitfield_name, bf_end, bf_start = match.groups()
            bf_end = int(bf_end)
            bf_start = int(bf_start)
            mask_width = self.bf_range_to_mask_width(bf_start, bf_end)
        else:
            bitfield_name = bitfield_def
            mask_width = 1
        bitfield_mask = (mask_width << shift)
        return (bitfield_name, bitfield_mask, shift)

    def bf_range_to_mask_width(self, bf_start, bf_end):
        bitfield_width = (bf_end-bf_start)+1
        # (2^2)-1 => 4-1 => 3 -> 0b11
        # (2^3)-1 => 8-1 => 7 -> 0b111
        bitfield_mask = (2**bitfield_width)-1
        return bitfield_mask

    # https://stackoverflow.com/questions/50705563/proper-way-to-do-bitwise-difference-python-2-7
    # b_minus_a = b & ~a
    # a_minus_b = a & ~b
    def bitwise_diff(self, old_value, new_value):
        if old_value is None:
            old_value = 0
        set_bitmask =  (new_value & (~old_value))
        unset_bitmask = (old_value & (~new_value))
        return (unset_bitmask, set_bitmask)

#############################################################

    def _reg_known(self, b0):
        # return b0 in self.register_map[self.current_bank]
        return b0 in self.register_map[self.current_bank].keys()

    def _reg_name(self, b0):
        return self.register_map[self.current_bank][b0]["name"]

    def _h(self, num):
        return "0x{:02X}".format(num)

    def _b(self, num):
        return "0b %s %s" % (format(num >> 4, "04b"), format((num & 0b1111), "04b"))
        # return format(num, "#010b")

def _b( num):
    return "0b %s %s" % (format(num >> 4, "04b"), format((num & 0b1111), "04b"))
    # return format(num, "#010b")

if __name__ == "__main__":
    if len(argv) < 3:
        raise RuntimeError("poo")
    source_files = sys.argv[2:]
    map_loader = None

    if source_files[0].endswith(".json"):
        from json_loader import JSONRegisterMapLoader
        map_loader = JSONRegisterMapLoader(source_files[0])
    elif source_files[0].endswith(".csv"):
        from csv_loader import CSVRegisterMapLoader
        map_loader = CSVRegisterMapLoader(source_files)
    if map_loader.map is None :
        raise AttributeError("MAP is None")

    decoder = RegisterDecoder(register_map=map_loader.map)

    with open(sys.argv[1], newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row_num, row in enumerate(reader):
            decoder.decode(row_num, row)

