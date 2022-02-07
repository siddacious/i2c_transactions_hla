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

from collections import namedtuple
from bitfield_list import *
from max98091_full import max_map

# in: WEED RegAddr: 0x08 Bytes: [0x00]
# out: [{'address': 8, 'name': 'MIC/DIRECT TO ADC'}, bytearray(b'\x00'), ''] 


# reg byte: bytearray(b'\x00') len: 1


# in: WEED RegAddr: 0x09 Bytes: [0x00]
# out: [{'address': 9, 'name': 'LINE TO ADC'}, bytearray(b'\x00'), ''] 


# reg byte: bytearray(b'\x00') len: 1


# in: WEED RegAddr: 0x0A Bytes: [0x00]
# out: [{'address': 10, 'name': 'ANALOG MIC LOOP'}, bytearray(b'\x00'), ''] 


DEBUG = 1
VERBOSE = True
ROW_NUMBER_OFFSET = 2
ROW_NUMBER_OFFSET = 2

BitField = namedtuple("BitField", "bitfield_name bitfield_mask shift")
Reg = namedtuple("Reg", "bitmask address")
RegisterOperation = namedtuple("RegisterOperation", "register_name bitfield_ops")

class Register:
    def __init__(self, address, info_obj):
        self._address = address
        self._oracle = info_obj # -> oracle generator? something to....do something

    @property
    def bitmask(self):
        return self._oracle.bitmask

    @property
    def address(self):
        return self._address

class RegisterMap:
    register_map_dict = max_map

    @classmethod
    def get(cls, register_address):
        if register_address in cls.register_map_dict:
            return cls.register_map_dict[register_address]
        return None

    @classmethod
    @property
    def registers(self):
        return {"this": "is", "a": "dictionary"}
    @classmethod
    def __getitem__(self, key):
        """Look up a register by address. Address can be an int or string representation of an int"""
        if isinstance(key, str):
            key = int(key)

        return self._map_dict[key]
class RegisterTraffic:
    def __init__(self, register_address, bytes, is_write):
        self._is_write = is_write
        self._bytes = bytes
        self._register_address = register_address
        self._register = RegisterMap[register_address]

    @property
    def is_write(self): return self._is_write

    @property
    def bytes(self): return self._bytes

    @property
    def address(self): return self._register.address
class RegisterDecoder:

    def __init__(self):
        self.register_width = 1
        self.cvs = {

        }
        self.register_map = max_map

        self.prev_single_byte_write = None

    def decode_transaction(self, reg_txn):
        """Decode a given RegisterOperation as a *thing*"""
        print("\n\nin:", reg_txn)
        register_changes = []
        try:
            register_changes = self.process_register_transaction(
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


        print("out:", register_changes, "\n\n")
        return register_changes

    def process_register_transaction(self, register_address, data, is_write):
        """Update register state cache and return the transaction summary for the current register state"""

        register_changes = []
        for address_offset, value_byte in enumerate(data):

            current_address = register_address+(address_offset * self.register_width)

            register = RegisterMap.get(current_address)
            if register is None:
                break
            bitfield_changes = self.decode_by_bitfield(register, value_byte, is_write)
            register_changes += (register, data, bitfield_changes)

        return register_changes

    def decode_by_bitfield(self, register, new_value, is_write):

        if not is_write:
            return ""

        load_bitfields(register)

        change_masks = self.change_masks(new_value, is_write, register)

        return self.bitfield_changes_list(new_value, register, register['bitfields'], change_masks)

    # This can be thought of as a "handler" for bitfield diffs. It could just as easily
    # return a heatmap for the bitfields, etc.
    def bitfield_changes_list(self, new_value, register, bitfields, change_masks):
        # for each of the bitfields, check to see if its mask overlaps with the set or unset masks
        # assemble a complete change string from the change strings of the bitfields inside
        changes = []

        unset_bitmask, set_bitmask = change_masks
        for bitfield in bitfields:
            if bitfield == "":
                print(f"FUNKY BF: {bitfield.__repr__()}({type(bitfield)}")
                print(f"Reg: {register}")
            # get the name, mask, and shift for the bitfield!!! # TODO: bitfield Class refactor
            bf_name, bf_mask, bf_shift = bitfield
            # mark changed if the set or unset masks overlap the bitfield's mask
            bf_changed = (bf_mask & set_bitmask) > 0 or  (bf_mask & unset_bitmask) > 0
            # if there was a change, append the change
            if bf_changed:
                # get a string representation of the change
                # instead, add string to list
                changes.append(self.bitfield_change_str(bitfield, new_value))
        return changes

    def bitfield_change_str(self, bitfield, new_value):

        bf_name, bf_value = self.bitfield_change(bitfield, new_value)
        bf_change_str = self.map_bf_value_to_cv(bf_name, bf_value)
        return bf_change_str

    def change_masks(self, new_value, is_write, register):
        ########################################
        # Read the Old Value from a cache, after trying to determine whiat key to use
        # Use the new and old values to determine which bits were changed and from what to what
        old_value = self.update_fetch_cache(register, is_write, new_value)
        unset_bitmask, set_bitmask = self.bitwise_diff(old_value, new_value)
        return (unset_bitmask, set_bitmask)

    # NB: This conflates outgoing and incomit register changes. 'old value' can be either the last
    # thing we sent, or the last thing we received. Both are valid 'old value's, however their
    # delta with a new value represent a change by the sensor (last write != new read) or a change
    # in value initiated by us/MCU
    # changes by the sensor are most likely to be either an interrupt firing or status reset/end
    # RO registers don't have "changes" in this sense
    # changes by the mcu are "commands" from the MCU, presumably to change a setting
    #### ONCE AGAIN  (I'M SURE) THIS IS THE MOST IMPORTANT NOW

    # RO reads (sensor provided data) are best decoded as their 'real' value after being transformed

    # this should perhaps move into a register state thing
    def update_fetch_cache(self, register, is_write, new_value):
        old_value = 0 # should this be None by default?

        if is_write:
            prev_key = 'last_read'
            current_key = 'last_write'
        else:
            prev_key = 'last_write'
            current_key = 'last_read'
        register[current_key] = new_value

        if prev_key in register:
            old_value = register[prev_key]

        return old_value

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

    def bitfield_change(self, bitfield, new_value):
        bf_name, bf_mask, bf_shift = bitfield

        # use the bitfield's mask and shift to get the bitfield's value
        bf_value = (bf_mask & new_value) >> bf_shift
        return bf_name,bf_value

    def map_bf_value_to_cv(self, bf_name, bf_value):

        cv_value = f"{bf_name}: {bin(bf_value)} 0x{bf_value:02X}"

        # let's get the hell out here !
        if not (bf_name in self.cvs):
            return cv_value

        bf_cv = self.cvs[bf_name]

        bf_value = bf_cv.get(bf_value)

        if bf_value == None:
            print(bf_name, "has no key: %s"%bf_value)

            # SAD PATH
            bf_value = bf_value
        return cv_value


######### THESE FUNCTIONS ONLY HAVE EACH OTHER #########################
    def single_byte_decode(self, is_write, b0):

        if is_write:
            current_register = self.register_map[b0]
            self.prev_single_byte_write = b0
            return "setup read from %s"%current_register['name']
        else: #READ
            if (self.prev_single_byte_write != None):

                return "%s read as %s (%s)"%(
                        self._reg_name(self.prev_single_byte_write),
                        self._b(b0),
                        self._h(b0))

    def decode_set_value(self, is_write, reg_addr, value_byte):

        # print("SET %s to %s (%s)" % (self._reg_name(reg_addr),  self._b(value_byte), self._h(value_byte)))

        return self.decode_by_bitfield(reg_addr, value_byte, is_write)

    def _reg_name(self, b0):
        return self.register_map[b0]["name"]

    def _h(self, num):
        return "0x{:02X}".format(num)

    def _b(self, num):
        return "0b %s %s" % (format(num >> 4, "04b"), format((num & 0b1111), "04b"))
        # return format(num, "#010b")

########################### /end sad f'ns ################################



if __name__ == "__main__":
    MockTrans = namedtuple("MockTrans", "register_address data write")
    decoder = RegisterDecoder()
    transactions = [
        #MockTrans(0x45, [0x00], True),
        #MockTrans(0x1B, [0x10], True),
        #MockTrans(0x1D, [0x60], True),
        MockTrans(0x2C, [0x04], True),
        #MockTrans(0x25, [0x01], True),
        # MockTrans(0x22, [0x04], True),
    ]
    for transaction in transactions:
        trans_string = decoder.decode_transaction(transaction)
    # get some test data
    # feed it to the thing
    # it should do some stuff
    print("you call register_decoder's main")
