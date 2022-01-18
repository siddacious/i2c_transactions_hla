#!/usr/bin/env python
"""

local/outgoing changes should always be printed
we don't want to see every failed poll for a self-clearing/status register
we always want to print data register reads

reads: data/sensors, state changes/polling,
-current bitfield values before an update; can be thought of as a setup for a write
signature: a> register <n>has more than one bitfield b> read to register <n>  immediately preceeding a write to <n>
first heuristic: read from register with > 1 bitfield can be skipped

"""
# TODO: option to print/report unchanged bitfields
# TODO: multi-byte register handling

# TODO: decode_by_bitfield needs to be reworked to use a register state object and register objects (or namedtuples)
# we don't care about incoming data nearly as much as outgoing data send by the library/driver

# TODO: Add support for decoding an arbitrary number of bytes
# check for a first byte

# TODO: make a Bitfield object or namedtuple

import sys
import csv
import re
import itertools
from sys import argv
from os.path import exists
from pickle import load
from struct import unpack_from


from bitfield_list import *

DEBUG = 1
VERBOSE = True
ROW_NUMBER_OFFSET = 2
ROW_NUMBER_OFFSET = 2
bank0 = None
bank1 = None

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


from collections import namedtuple
BitField = namedtuple("BitField", "bitfield_name bitfield_mask shift")




max_map = {
    0: {

	0x22: {
        'address': 0x22,
        'name': "INTERFACE FORMAT",
        'last_read_value': None,
        'reset_value': 0x00,
        'raw_string': r"— — RJ WCI	BCI	DLY	WS[1:0]"
    },
	0x29: {
        'address': 0x29,
        'name': "LEFT HP MIXER",
        'last_read_value':	None,
        'reset_value': 0x00,
        'raw_string': r"— — MIXHPL[5:0]"
    },
	0x2A: {
        'address': 0x2A,
        'name': "RIGHT HP MIXER",
        'last_read_value': None,
        'reset_value': 0x00,
        'raw_string': r"— — MIXHPR[5:0]"
    },
	0x2B: {
        'address': 0x2B,
        'name' :"HP CONTROL",
        'last_read_value': None,
        'reset_value': 0x00,
        'raw_string': r"— — MIXHP RSELMIXHP LSEL MIXHPRG[1:0] MIXHPLG[1:0]"
    },
	0x2C: {
        'address': 0x2C,
        'name': "LEFT HP VOLUME",
        'last_read_value': None,
        'reset_value': 0x1A,
        'raw_string': r"HPLM — — HPVOLL[4:0]"
    },
	0x2D: {
        'address': 0x2D,
        'name': "RIGHT HP VOLUME",
        'last_read_value': None, # R/W
        'reset_value': 0x1A,
        'raw_string': r"HPRM — — HPVOLR[4:0]"
    },
    0x3F: {
        'address': 0x3F,
        'name': "OUTPUT ENABLE",
        'last_read_value': None,
        'reset_string': 0x00, # R/W
        'raw_string': "HPREN	HPLEN	SPREN	SPLEN	RCVLEN	RCVREN	DAREN  DALEN"
    },
    0x41: {
        'address': 0x41,
        'name': "DSP FILTER ENABLE",
        'last_read_value': None,
        'reset_string': 0x00, # R/W
        'raw_string': "—	—	—	DMIC2BQ EN	RECBQEN	EQ3BAND EN	EQ5BAND EN	EQ7BAND EN"
    },
    0x45: {
        'address': 0x45,
        'name': "DEVICE SHUTDOWN",
        'last_read_value': None,
        'reset_string': 0x00,
        'raw_string': "SHDN	—	—	—	—	—	—	—	" # R/W
    },
    0x1B: {
        'address': 0x1B,
        'name': "SYSTEM CLOCK",
        'last_read_value': None,
        'reset_string': 0x00, # R/W
        'raw_string': "—	—	PSCLK[1:0]	—	—	—	—	"
    },
    0x1D: {
        'address': 0x1D,
        'name': "CLOCK RATIO NI MSB",
        'last_read_value': None,
        'reset_string': 0x00,
        'raw_string': "—	NI[14:8]	" # R/W
    },
    0x25: {
        'address': 0x25,
        'name': "I/O CONFIGURATION",
        'last_read_value': None,
        'reset_string': 0x00,
        'raw_string': " —	—	LTEN	LBEN	DMONO	HIZOFF	SDOEN	SDIEN	" # R/W
    }
    }
}
class RegisterDecoder:

    def __init__(self, register_map={0:{}},
        log_path="/Users/bs/cp/Adafruit_CircuitPython_AS7341/reg.log",
        pickled_map_path="/Users/bs/dev/tooling/i2c_txns/maps/as7341_map_update.pickle",
        pickled_cvs_path="/Users/bs/dev/tooling/i2c_txns/maps/as7341_cv.pickle"):
        self.register_width = 1
        self.cvs = {}
        self.register_map = max_map

        self.prev_single_byte_write = None
        self.current_bank = 0
        if pickled_cvs_path:
            if exists(pickled_cvs_path):
                self.cvs  = load( open( pickled_cvs_path, "rb" ) )
            else:
                AttributeError("you must provide a pickled register map")

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
        if reg_txn.write: print("WRITE")
        if not reg_txn.write: print("READ")
        reg_txn_string = ""


        try:
            reg_txn_string = self.process_register_transaction(
                reg_txn.register_address,
                reg_txn.data,
                reg_txn.write
            )
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
            #reg_txn_string = self.default_txn_summary(reg_txn.register_address, reg_txn.data, reg_txn.write)
            reg_txn_string = "UNDECODED"
        print("\nin:", reg_txn)
        print("out:", reg_txn_string, "\n")
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

        #    def decode_by_bitfield(self, register_address, new_value, is_write):

        # # verify that we have a register
        register = self.get_register(register_address)
        # return f"Reg: {register['name']}, Data:{hex(byte)}"
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
    def decode_set_value(self, is_write, reg_addr, value_byte):

        debug_print("SET %s to %s (%s)" % (self._reg_name(reg_addr),  self._b(value_byte), self._h(value_byte)))

        return self.decode_by_bitfield(reg_addr, value_byte, is_write)

    def bitwise_diff(self, old_value, new_value):
        """
        https://stackoverflow.com/questions/50705563/proper-way-to-do-bitwise-difference-python-2-7
        b_minus_a = b & ~a
        a_minus_b = a & ~b
        """
        if old_value is None:
            old_value = 0
        set_bitmask =  (new_value & (~old_value))
        unset_bitmask = (old_value & (~new_value))
        return (unset_bitmask, set_bitmask)


    #######################################
    #
    # This function is TOO 000000000nG
    #
    #####################################
    def decode_by_bitfield(self, register_address, new_value, is_write):

        # verify that we have a register
        register = self.get_register(register_address)
        if not register:
            return self.default_txn_summary(register_address, new_value, is_write)

        ######################################################################
        # Get bitfield masks, names, etc. from raw field string:
        # This can and should be loaded and cached at startup
        bitfields = load_bitfields(register)

        ########################################
        # Read the Old Value from a cache, after trying to determine whiat key to use
        # Use the new and old values to determine which bits were changed and from what to what
        if is_write:
            prev_key = 'last_read'
            current_key = 'last_write'
        else:
            prev_key = 'last_write'
            current_key = 'last_read'
        old_value = 0
        changes_str = f"{register['name'].title()}  --  "
        register[current_key] = new_value

        if prev_key in register:
            old_value = register[prev_key]
        unset_bitmask, set_bitmask = self.bitwise_diff(old_value, new_value)


        ### print diff, kinda

        #### STRINGIFY #####
        # for each of the bitfields, check to see if its mask overlaps with the set or unset masks
        # assemble a complete change string from the change strings of the bitfields inside
        bf_change_str = ""
        for bitfield in bitfields:
            # get the name, mask, and shift for the bitfield!!! # TODO: bitfield Class refactor
            bf_name, bf_mask, bf_shift = bitfield

            # mark changed if the set or unset masks overlap the bitfield's mask
            bf_changed = (bf_mask & set_bitmask) > 0 or  (bf_mask & unset_bitmask) > 0
            byte_changed = (unset_bitmask > 0) or (set_bitmask > 0) # WUT

            # get a string representation of the change
            bf_change_str = self.bitfield_change_str(bitfield, unset_bitmask, set_bitmask, new_value)

            # if there was a change, append the change
            if bf_changed:
                changes_str += bf_change_str+", "

        # return something
        if is_write:
            return changes_str
        return ""


    def get_register(self, register_address):
        """
        register structure
        {
            'address': 0x2A,
            'name': "RIGHT HP MIXER",
            'last_read_value': None,
            'reset_value': 0x00,
            'raw_string': r"— — MIXHPR[5:0]"  # <<< used in broken code
        },
        """
        if self._reg_known(register_address):
            return self.register_map[self.current_bank][register_address]
        return None

    def bitfield_change_str(self, bitfield, unset_bitmask, set_bitmask, new_value):

        bf_name, bf_mask, bf_shift = bitfield
        bf_value = (bf_mask & new_value) >> bf_shift

        # bf_set = (bf_mask & set_bitmask) > 0
        # bf_unset = (bf_mask & unset_bitmask) > 0

        # change_str = None


        # if not bf_changed:
        #     return None

        if bf_name in self.cvs:
            print("bf has CV:")
            bf_cv = self.cvs[bf_name]
            try:
                bf_value = bf_cv[bf_value]
            except KeyError as e:
                print(bf_name, "has no key: %s"%bf_value)
                pretty(bf_cv)
                # maybe print something other than hext
                bf_value = self._h(bf_value)

        else:
            bf_value = self._h(bf_value)
        change_str = "%s : %s"%(bf_name, bf_value)
        return change_str

###################################################

    def _reg_known(self, b0):
        # print("b0", b0, "bank", self.current_bank, "map", self.register_map)
        # return b0 in self.register_map[self.current_bank]
        return b0 in self.register_map[self.current_bank].keys()

    def _reg_name(self, b0):
        return self.register_map[self.current_bank][b0]["name"]

    def _h(self, num):
        return "0x{:02X}".format(num)

    def _b(self, num):
        return "0b %s %s" % (format(num >> 4, "04b"), format((num & 0b1111), "04b"))
        # return format(num, "#010b")

if __name__ == "__main__":

    MockTrans = namedtuple("MockTrans", "register_address data write")
    decoder = RegisterDecoder()
    transaction = MockTrans(0x1D, [0x60], True)
    trans_string = decoder.decode_transaction(transaction)
    # get some test data
    # feed it to the thing
    # it should do some stuff
    print("you call register_decoder's main")
