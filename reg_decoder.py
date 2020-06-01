#!/usr/bin/env python
import sys
import csv
import re
import itertools

DEBUG = False
VERBOSE = False
ROW_NUMBER_OFFSET = 2
bank0 = None
bank1 = None

BITFIELD_REGEX = '^([^\[]+)\[(\d):(\d)\]$' # matches WHO_AM_I[7:0], DISABLE_ACCEL[5:3] etc.

def debug_print(*args, **kwargs):
    if DEBUG:
        print("\t\t\t\t\tDEBUG:", *args, **kwargs)


def verbose_print(*args, **kwargs):
    if VERBOSE:
        print("LOG:", *args, **kwargs)

def verbose_debug(*args, **kwargs):
    if VERBOSE and DEBUG:
        verbose_print("DEBUG:", *args, **kwargs)

class RegisterDecoder:
    def __init__(self, csv_files=None, serial_device=None):
        self.banks_dict = {0: {}, 1: {}, 2: {}, 3: {}, -1:{127:{'name': 'REG_BANK_SEL', 'address': 127, 0: '', 1: '', 2: '', 3: '', 4: 'USER_BANK[1:0]', 5: 'USER_BANK[1:0]', 6: '', 7: '', 'last_read_value': None}}}
        for index, csv_file in enumerate(csv_files):
            self.parse_csv_bank(csv_file, index)
        # when to clear? consume on read match
        self.prev_single_byte_write = None
        self.current_bank = -1

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

        rw = row["rw"]

        # TODO: Add support for an arbitrary number of bytes
        # check for a first byte
        b0 = int(row["byte0"], 16)
        # like UNKNOWN
        if rw == "WRITE" and (b0 != 0x7F) and (not self._reg_known(b0)):
            print(
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

        # check for a second byte
        if "byte1" in row.keys() and len(row["byte1"].strip()) > 0:
            b1 = int(row["byte1"], 16)

        verbose_print("\tRow number:", row_num, "row:", row)

        ########### Decode #################
        self.decode_bytes(rw, b0, b1)

    def decode_bytes(self, rw, b0, b1):
        if b1 is None:
            self._single_byte_decode(rw, b0)
        elif rw == "WRITE":
            self._decode_set_value(rw, b0, b1)
        else:
            raise RuntimeError("Multi-byte reads not supported")


    def _single_byte_decode(self, rw, b0):

        if rw == "WRITE":
            current_register = self.banks_dict[self.current_bank][b0]

            print("\n\tSETRD %s (%s)" % (self._reg_name(b0), self._h(b0)))
            self.prev_single_byte_write = b0
        else:
            current_register = self.banks_dict[self.current_bank][self.prev_single_byte_write]

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
                raise ("UNEXPECTED READ WITHOUT PREV WRITE")


    def _decode_set_value(self, rw, reg_addr, value_byte):
        print(rw, reg_addr, value_byte)

        current_register = self.banks_dict[self.current_bank][reg_addr]

        # TODO: check this by name
        # ******* SET BANK **************
        if reg_addr == 0x7F:
            self.current_bank = value_byte >> 4
            return
        # ****IDENTIFIED WRITE TO REG W/ NEW VALUE ***
        print("SET %s to %s (%s)" % (self._reg_name(reg_addr),  self._b(value_byte), self._h(value_byte)))
        old_value = current_register['last_read_value']
        # FIND BITS THAT HAVE CHANGED
        bitwise_diffs = self._bitwise_diff(old_value, value_byte)

        # NOTHING CHANGED
        if len(bitwise_diffs) is 0:
            return

        self._decode_bitfields(bitwise_diffs, current_register, value_byte)
        print("")

    def _decode_bitfields(self, bitwise_diffs, current_register, value_byte):
        for bitfield_def, group_iterator in self._group_bitwise_diffs_by_bitfield_def(bitwise_diffs, current_register):

            match = re.fullmatch(BITFIELD_REGEX, bitfield_def)
            # NAMED BITFIELD UPDATED
            if match: #
                name, msb_str, lsb_str = match.groups()
                bitfield_msb = int(msb_str)
                bitfield_lsb = int(lsb_str)
                bitfield_value = self._extract_bitfield_val_from_byte(value_byte, bitfield_msb, bitfield_lsb)
                print("\t%s"%name,  "now HHet to", self._h(bitfield_value)) # check that this is called when we know the old value
            # SINGLE BIT W/ NAME
            else:
                group = list(group_iterator)
                bitfield_name = bitfield_def
                bitfield_value = bool(group[0][1])
                print("\t%s is now zzet to %s"%(bitfield_name, bitfield_value))

    def _bitwise_diff(self, old_value, new_value):
        if old_value is None:
            old_value = 0
        changed_bits = old_value ^ new_value
        changes = []
        for shift in range(7, -1, -1):
            if changed_bits >>shift & 0b1:
                new_bit_value = (new_value & 1<<shift) >> shift
                changes.append((shift, new_bit_value))
        return changes


    def _extract_bitfield_val_from_byte(self, value_byte, msb, lsb):
        """Extract the value of bitfield from a byte using a returned match object"""
        # determine the mask width exponent  from [3:0]-> 3-(0+1) = 2
        bitfield_width_exponent = msb-lsb+1
        # (2^2)-1 =>> (2**2)-1 = 4-1 =>> 3 -> 0b11 or 2^3 -1 = 8-1 = 7 -> 0b111
        bitfield_mask = (2**bitfield_width_exponent)-1
        bitfield_mask <<= lsb
        bitfield_value = (value_byte & bitfield_mask) >>lsb

        return bitfield_value

    def _reg_known(self, b0):
        return b0 in self.banks_dict[self.current_bank].keys()

    def _reg_name(self, b0):
        return self.banks_dict[self.current_bank][b0]["name"]

    def _group_bitwise_diffs_by_bitfield_def(self, bitwise_diffs, register_def):
        bitfield_def = lambda x: register_def[x[0]]
        return itertools.groupby(bitwise_diffs, bitfield_def)

    def _h(self, num):
        return "0x%s" % format(num, "02X")

    def _b(self, num):
        return "0b %s %s" % (format(num >> 4, "04b"), format((num & 0b1111), "04b"))
        # return format(num, "#010b")

    def parse_csv_bank(self, filename, bank_number=0):
        bank = self.banks_dict[bank_number]
        with open(filename, newline="") as csvfile:
            bank_dict_reader = csv.DictReader(csvfile)
            # ['ADDR (HEX)', 'ADDR (DEC.)', 'REGISTER NAME', 'SERIAL I/F', 'BIT7', 'BIT6', 'BIT5', 'BIT4', 'BIT3', 'BIT2', 'BIT1', 'BIT0']
            for row in bank_dict_reader:
                reg = {}
                # verbose_debug(row)
                reg["name"] = row["REGISTER NAME"]
                dec_addr = row["ADDR (DEC.)"]
                address= int(dec_addr)
                reg["address"] = address
                for bit_index in range(8):
                    reg[bit_index] = row["BIT%d"%bit_index]
                reg['last_read_value'] = None
                bank[address] = reg


if __name__ == "__main__":
    banks_dict = {}
    # print("\n************* Reading Register Map ****************\n")

    decoder = RegisterDecoder(
        csv_files=["bank0.csv", "bank1.csv", "bank2.csv", "bank3.csv"]
    )
    print("\n************* Parsing *****************************\n")
    with open(sys.argv[1], newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row_num, row in enumerate(reader):
            decoder.decode(row_num, row)
