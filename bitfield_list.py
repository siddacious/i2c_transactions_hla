import re
from collections import namedtuple

BitField = namedtuple("BitField", "")

BITFIELD_REGEX = '^([^\[]+)\[(\d):(\d)\]$' # matches WHO_AM_I[7:0], DISABLE_ACCEL[5:3] etc.

class BitfieldList:
    @staticmethod
    def load_bitfields(current_register):
        """
        def get_register(self, register_address):
        if self._reg_known(register_address):
            return self.register_map[self.current_bank][register_address]
        return None

        This function is supposed to fill out _something_ from a bitfield def:
        The start, end, and a mask that fits the width; with which it can presumably identify its part of the byte
        Strangely, I feel like the ultimate data here is a name, and a mask that can be used as is against data
        git byte, mask it , return with name? or
        name, mask = ....
        collection[name] = byte & mask >>shift
        """
        if 'bitfields' in current_register:
            return current_register['bitfields']

        bitfields = []

        prev_bitfield_name = None
        print("Current register:", current_register)
        """
        Current register: {
            'address': 34,
            'name': 'INTERFACE FORMAT',
            'last_read_value': None,
            'reset_value': 0,
            'raw_string': '— — RJ WCI\tBCI\tDLY\tWS[1:0]'}
        EXCEPTION
        <class 'KeyError'>
        (0,)
        0
        """
        for idx in range(8): # assumes fields have been built out
            bitfield_def = current_register[idx]
            bitfield_name, bitfield_mask, bitfield_shift = BitfieldList.bitfield_def_to_bitfield(bitfield_def, idx)
            print("bitfield_name", bitfield_name, "bitfield_mask", "{:#010b}".format(bitfield_mask), "bitfield_shift", bitfield_shift)

            # If name is none (unused field) or the same as previous (bitfield)
            if not bitfield_name or (prev_bitfield_name == bitfield_name):
                continue

            bitfields.append((bitfield_name, bitfield_mask, bitfield_shift))
            prev_bitfield_name = bitfield_name
        current_register['bitfields'] = bitfields

        return current_register['bitfields']

    @staticmethod
    def bitfield_def_to_bitfield(bitfield_def, shift):
        match = re.fullmatch(BITFIELD_REGEX, bitfield_def)
        if match: #
            bitfield_name, bf_end, bf_start = match.groups()
            bf_end = int(bf_end)
            bf_start = int(bf_start)
            mask_width = BitfieldList.bf_range_to_mask_width(bf_start, bf_end)
            print("end", bf_end, "start", bf_start, "mask" , mask_width)
        else:
            bitfield_name = bitfield_def
            mask_width = 1
        bitfield_mask = (mask_width << shift)
        return (bitfield_name, bitfield_mask, shift)

    @staticmethod
    def bf_range_to_mask_width(bf_start, bf_end):
            bitfield_width = (bf_end-bf_start)+1
            # (2^2)-1 => 4-1 => 3 -> 0b11
            # (2^3)-1 => 8-1 => 7 -> 0b111
            bitfield_mask = (2**bitfield_width)-1
            return bitfield_mask
