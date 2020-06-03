#!/usr/bin/env python
import sys
import csv
import re
import itertools

from sys import argv

DEBUG = False
VERBOSE = False
ROW_NUMBER_OFFSET = 2
ROW_NUMBER_OFFSET = 2
bank0 = None
bank1 = None

BITFIELD_REGEX = '^([^\[]+)\[(\d):(\d)\]$' # matches WHO_AM_I[7:0], DISABLE_ACCEL[5:3] etc.

def debug_print(*args, **kwargs):
    if DEBUG:
        print("\t\t\t\t\tDEBUG:", *args, **kwargs)

def newp(new_s, tabs=6):
    print("%s         \t%s"%("\t"*tabs, new_s))

def verbose_print(*args, **kwargs):
    if VERBOSE:
        print("LOG:", *args, **kwargs)

def verbose_debug(*args, **kwargs):
    if VERBOSE and DEBUG:
        verbose_print("DEBUG:", *args, **kwargs)

class RegisterDecoder:

    def __init__(self, register_map=None):
        self.register_map = register_map
        self.prev_single_byte_write = None
        self.current_bank = -1

    def decode(self, row_num, row):
        if len(self.register_map) is 1 and self.current_bank is -1:
            self.current_bank = 0
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

        rw = row["rw"]

        # TODO: Add support for an arbitrary number of bytes
        # check for a first byte
        b0 = int(row["byte0"], 16)

        if rw == "WRITE" and (b0 != 0x7F) and (not self._reg_known(b0)):
            verbose_print(
                "\n\t\tBAD KEY:",
                b0,
                "(%s)" % self._h(b0),
                "self.current_bank:",
                self.current_bank,
                "RW:",
                rw,
                "Row number:",
                adjusted_row_num,
            )
            return

        if "byte1" in row.keys() and len(row["byte1"].strip()) > 0:
            b1 = int(row["byte1"], 16)
        verbose_print("\tRow number:", row_num, "row:", row)

        ########### Decode #################
        self.decode_bytes(rw, b0, b1)

    def decode_bytes(self, rw, b0, b1):
        if b1 is None:
            self.single_byte_decode(rw, b0)
        elif rw == "WRITE":
            self.decode_set_value(rw, b0, b1)
        else:
            #raise RuntimeError("Multi-byte reads not supported")
            return

    def single_byte_decode(self, rw, b0):

        if rw == "WRITE":
            current_register = self.register_map[self.current_bank][b0]
            bitfields = self.load_bitfields(current_register)
            print("\n\tSETRD %s (%s)" % (self._reg_name(b0), self._h(b0)))
            self.prev_single_byte_write = b0
        else:
            current_register = self.register_map[self.current_bank][self.prev_single_byte_write]
            bitfields = self.load_bitfields(current_register)
            if (
                self.prev_single_byte_write != None
            ):  # isn't this always going to be set in this case? for normal register'd i2c yes.
                print("\t_READ %s (%s)" % (self._b(b0), self._h(b0)))
                print(
                    "%s read as %s (%s)"
                    % (
                        self._reg_name(self.prev_single_byte_write),
                        self._b(b0),
                        self._h(b0),
                    )
                )
                current_register['last_read_value'] = b0
                self.prev_single_byte_write = None  # shouldn't be needed
            else:
                raise ("UNEXPECTED READ WITHOUT PRECEDING WRITE")

    def decode_set_value(self, rw, reg_addr, value_byte):
        current_register = self.register_map[self.current_bank][reg_addr]
        bitfields = self.load_bitfields(current_register)

        # TODO: check this by name
        # ******* SET BANK **************
        if reg_addr == 0x7F:
            self.current_bank = value_byte >> 4
            return
        # ****IDENTIFIED WRITE TO REG W/ NEW VALUE ***
        print("SET %s to %s (%s)" % (self._reg_name(reg_addr),  self._b(value_byte), self._h(value_byte)))
        old_value = current_register['last_read_value']

        print("")
        self.decode_by_bitfield(current_register, value_byte)
        print("")

    def decode_by_bitfield(self, current_register, new_value):
        old_value = current_register['last_read_value']
        bitfields = self.load_bitfields(current_register)

        self.print_bitfield_changes(old_value, new_value, bitfields)

    def print_bitfield_changes(self, old_value, new_value, bitfields):
        unset_bitmask, set_bitmask = self.bitwise_diff(old_value, new_value)
        for bitfield in bitfields:
            bf_change_str = self.bitfield_change_str(bitfield, unset_bitmask, set_bitmask, new_value)
            if bf_change_str:
                print(bf_change_str)

    def bitfield_change_str(self, bitfield, unset_bitmask, set_bitmask, new_value):
        bf_name, bf_mask, bf_shift = bitfield
        change_str = None
        #newp("'%s' =>%s"%(bf_name, format(bf_mask, "#010b")), 3)
        if bf_mask == 0b1:
            if (bf_mask & unset_bitmask):
                change_str = "\t\t%s was unset"%bf_name
            if (bf_mask & set_bitmask):
                change_str = "\t\t%s was set"%bf_name
        else:
            if (bf_mask & unset_bitmask) or (bf_mask & set_bitmask):
                bf_value = (bf_mask & new_value)>>bf_shift
                change_str = "\t\t%s was changed to %s"%(bf_name, hex(bf_value))

        return change_str

    def load_bitfields(self, current_register):
        if 'bitfields' not in current_register:
            bitfields = []
            prev_bitfield_name = None
            for idx in range(8):
                bitfield_def = current_register[idx]
                bitfield_name, bitfield_mask, bitfield_shift = self.bitfield_def_to_bitfield(bitfield_def, idx)

                if not bitfield_name or (prev_bitfield_name == bitfield_name):
                    continue
                # print("name:", bitfield_name, "mask: %s shift: %d"%(format(bitfield_mask,"#010b"), bitfield_shift))
                bitfields.append((bitfield_name, bitfield_mask, bitfield_shift))
                prev_bitfield_name = bitfield_name
            current_register['bitfields'] = bitfields
        return current_register['bitfields']
        bitfields

    def bitfield_def_to_bitfield(self, bitfield_def, shift):
        match = re.fullmatch(BITFIELD_REGEX, bitfield_def)
        if match: #
            bitfield_name, bf_end, bf_start = match.groups()
            bf_end = int(bf_end)
            bf_start = int(bf_start)
            bitfield_mask = self.bitfield_range_to_mask(bf_start, bf_end)
        # SINGLE BIT W/ NAME
        else:
            bitfield_name = bitfield_def
            bitfield_mask = (1 << shift)
        return (bitfield_name, bitfield_mask, shift)

    def bitfield_range_to_mask(self, bf_start, bf_end):
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
        return b0 in self.register_map[self.current_bank].keys()

    def _reg_name(self, b0):
        return self.register_map[self.current_bank][b0]["name"]

    def _h(self, num):
        return "0x%s" % format(num, "02X")

    def _b(self, num):
        return "0b %s %s" % (format(num >> 4, "04b"), format((num & 0b1111), "04b"))
        # return format(num, "#010b")

if __name__ == "__main__":
    if len(argv) < 3:
        raise RuntimeError("poo")
    source_files = sys.argv[2:]
    map_loader = None

    if source_files[0].endswith(".json"):
        from register_decoder.map_loader.json_loader import JSONRegisterMapLoader
        map_loader = JSONRegisterMapLoader(source_files[0])
    elif source_files[0].endswith(".csv"):
        from register_decoder.map_loader.csv_loader import CSVRegisterMapLoader
        map_loader = CSVRegisterMapLoader(source_files)
    if map_loader.map is None :
        raise AttributeError("MAP is None")

    decoder = RegisterDecoder(register_map=map_loader.map)

    with open(sys.argv[1], newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row_num, row in enumerate(reader):
            decoder.decode(row_num, row)
