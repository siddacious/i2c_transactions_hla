#!/usr/bin/env python

from collections import namedtuple

from bitfield_list import *

I2CWrite = namedtuple('I2CWrite', 'address data')
# 0x3f, 0x41, 0x45, 0x25
reference_map = {
    0: {
        0x22: {
            'address': 0x22,
            'name': "INTERFACE FORMAT",
            'last_read_value': None,
            'reset_value': 0x00,
            'raw_string': r"— — RJ WCI	BCI	DLY	WS[1:0]",
        },
        0x29: {
            'address': 0x29,
            'name': "LEFT HP MIXER",
            'last_read_value': None,
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
            'last_read_value': None,
            'reset_value': 0x1A,
            'raw_string': r"HPRM — — HPVOLR[4:0]"
        }
    }
}
BITFIELD_REGEX = '^([^\[]+)\[(\d):(\d)\]$' # matches WHO_AM_I[7:0], DISABLE_ACCEL[5:3] etc.
def expand_bitfield(bitfield_thing):

        bf_name, bf_end, bf_start = bitfield_thing.groups()
        bf_end = int(bf_end)
        bf_start = int(bf_start)
        bitfield_sized_mask = BitfieldList.bf_range_to_mask_width(bf_start, bf_end)

        bit_count = (bf_end - bf_start) +1 # "bf_start & bf_end are 0-based, counting is 1 based"
        if bit_count <= 1:
            return []

        # we know that we need to end with this many, including this
        return [ f"{bf_name}[{x}]" for x in range(bf_end, bf_start-1, -1)]

# why does it matter if a reg is expanded? it makes the bitfield bits more bitlike, but why?
#
def expand_reg(reg):
    # r"— — MIXHP RSELMIXHP LSEL MIXHPRG[1:0] MIXHPLG[1:0]"
    pieces = reg['raw_string'].split()
    expanded = []

    for idx, piece in enumerate(pieces):
        match = re.fullmatch(BITFIELD_REGEX, piece)
        if match:
            expanded.extend(expand_bitfield(match))
        else:
            if piece == "—":
                expanded.append("<WAK>")
            else:
                expanded.append(piece)

    return expanded

def handl_map(addr, reg):


    cells = expand_reg(reg)
    print(f"{hex(addr)}:", end=" ")
    for cell in cells:
        print(f"\t{cell}", end="")
    print("")


if __name__ == "__main__":
    print("\n\n++ Start ++")
    max_map = reference_map[0]
    for addr, reg in max_map.items():
        handl_map(addr, reg)

    print("++ Done ++\n\n")

from collections import namedtuple
I2CWrite = namedtuple('I2CWrite', 'address data')

writes = [


    I2CWrite(0x45, 0x00),
    I2CWrite(0x1B, 0x10),
    I2CWrite(0x1D, 0x60),
    I2CWrite(0x22, 0x04),
    I2CWrite(0x25, 0x01),
    I2CWrite(0x22, 0x04),
    I2CWrite(0x29, 0x00),
    I2CWrite(0x29, 0x00),
    I2CWrite(0x29, 0x00),
    I2CWrite(0x29, 0x00),
    I2CWrite(0x29, 0x00),
    I2CWrite(0x29, 0x00),
    I2CWrite(0x2A, 0x00),
    I2CWrite(0x2A, 0x00),
    I2CWrite(0x2A, 0x00),
    I2CWrite(0x2A, 0x00),
    I2CWrite(0x2A, 0x00),
    I2CWrite(0x2A, 0x00),
    I2CWrite(0x2B, 0x00),
    I2CWrite(0x2B, 0x00),
    I2CWrite(0x2C, 0x07),
    I2CWrite(0x2D, 0x07),
    I2CWrite(0x2C, 0x07),
    I2CWrite(0x2D, 0x07),
    I2CWrite(0x3F, 0x40),
    I2CWrite(0x3F, 0xC0),
    I2CWrite(0x3F, 0xC1),
    I2CWrite(0x3F, 0xC3),
    I2CWrite(0x41, 0x00),
    I2CWrite(0x45, 0x80),
]
