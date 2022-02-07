from cmath import exp
import re
from collections import namedtuple

BitField = namedtuple("BitField", "")

BITFIELD_REGEX = '([^\[]+)\[(\d+):(\d+)\]' # matches WHO_AM_I[7:0], DISABLE_ACCEL[5:3] etc.
def expand_bitfield(bitfield_thing):

        bf_name, bf_end, bf_start = bitfield_thing.groups()
        bf_end = int(bf_end)
        bf_start = int(bf_start)
        bitfield_sized_mask = bf_range_to_mask_width(bf_start, bf_end)

        bit_count = (bf_end - bf_start) +1 # "bf_start & bf_end are 0-based, counting is 1 based"
        if bit_count <= 1:
            return []

        # we know that we need to end with this many, including this
        return [ f"{bf_name}[{bf_end}:{bf_start}]" for x in range(bf_end, bf_start-1, -1)]
        # return [ f"{bf_name}[{x}]" for x in range(bf_end, bf_start-1, -1)]

def expand_reg(reg):
    # r"— — MIXHP RSELMIXHP LSEL MIXHPRG[1:0] MIXHPLG[1:0]"

    raw_string = reg.get('raw_string')
    if raw_string is None:
        return reg
    pieces = reg['raw_string'].split()
    expanded = []

    for idx, piece in enumerate(pieces):
        match = re.fullmatch(BITFIELD_REGEX, piece)
        if match:
            expanded.extend(expand_bitfield(match))
        else:
            if piece == "—":
                expanded.append("")
            else:
                expanded.append(piece)

    return expanded

def load_bitfields(register_obj):
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
    if  'bitfields' in register_obj:
        return register_obj['bitfields']

    bitfields = []

    prev_bitfield_name = None
    expanded_bitfields = register_obj['expanded_bitfields']
    expanded_bitfields.reverse()
    for idx in range(8): # assumes fields have been built out
        bitfield_def = expanded_bitfields[idx] # <- treating like register_obj is a list of bitfield defs
        bitfield_name, bitfield_mask, bitfield_shift = bitfield_def_to_bitfield(bitfield_def, idx)

        # If name is none (unused field) or the same as previous (bitfield)
        if not bitfield_name or (prev_bitfield_name == bitfield_name):
            continue

        bitfields.append((bitfield_name, bitfield_mask, bitfield_shift))
        prev_bitfield_name = bitfield_name
    register_obj['bitfields'] = bitfields
    return

def bf_range_to_mask_width(bf_start, bf_end):
        bitfield_width = (bf_end-bf_start)+1
        # (2^2)-1 => 4-1 => 3 -> 0b11
        # (2^3)-1 => 8-1 => 7 -> 0b111
        bitfield_mask = (2**bitfield_width)-1
        return bitfield_mask

def bitfield_def_to_bitfield(bitfield_def, shift):
    match = re.fullmatch(BITFIELD_REGEX, bitfield_def)
    if match: #
        bitfield_name, bf_end, bf_start = match.groups()
        bf_end = int(bf_end)
        bf_start = int(bf_start)
        mask_width = bf_range_to_mask_width(bf_start, bf_end)
    else:
        bitfield_name = bitfield_def
        mask_width = 1
    bitfield_mask = (mask_width << shift)
    return (bitfield_name, bitfield_mask, shift)
