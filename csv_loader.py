from sys import argv
from csv import DictReader, DictWriter
import json
import os
class RegisterMapLoader:
    def __init__(self, map_source=None):
        self.map_source = map_source
        self._map = None
        self.load_map()
        self.generate_bitfield_masks()

    def load_map(self):
        if self.map_source is None:
            raise AttributeError("Base Class", self.__name__, "cannot be instantiated directly")
    @property
    def map(self):
        """The object representing the register map"""
        return self._map

    def generate_bitfield_masks(self):
        pass
    # in: bitswise diffs? current_reg current value
    def _get_bitfields(self, current_register):
        if 'bitfields' not in current_register:
            bitfields = []
            prev_bitfield = None
            for idx in range(8):
                bitfield_def = current_register[idx]
                bitfield = self.extract_bitfield_mask(bitfield_def, idx)
                if prev_bitfield == bitfield or (not bitfield[0]):
                    continue
                bitfields.append(bitfield)
                prev_bitfield = bitfield
            current_register['bitfields'] = bitfields
        return current_register['bitfields']
        bitfields

    def extract_bitfield_mask(self, bitfield_def, idx):
        match = re.fullmatch(BITFIELD_REGEX, bitfield_def)
        # NAMED BITFIELD UPDATED
        if match: #
            bitfield_name, bf_end, bf_start = match.groups()
            bf_end = int(bf_end)
            bf_start = int(bf_start)
            bitfield_width_exponent = (bf_end-bf_start)+1
            # (2^2)-1 =>> (2**2)-1 = 4-1 =>> 3 -> 0b11 or 2^3 -1 = 8-1 = 7 -> 0b111
            bitfield_mask = (2**bitfield_width_exponent)-1
        # SINGLE BIT W/ NAME
        else:
            bitfield_name = bitfield_def
            bitfield_mask = (1 << idx)
        return (bitfield_name, bitfield_mask)
class CSVRegisterMapLoader(RegisterMapLoader):
    def __init__(self, csv_file=None, csv_files=None, serial_device=None):
        self._map = {0:{}}
        # self._map = {0: {}}
        # raise RuntimeError((csv_files))
        # raise RuntimeError(str(csv_files))
        if csv_file and not csv_files:
            csv_files = [csv_file]
        for index, csv_file in enumerate(csv_files):
            self.parse_csv_bank(csv_file, index)
        # when to clear? consume on read match
        self.prev_single_byte_write = None

    def parse_csv_bank(self, filename, bank_number=0):
        bank = self.map[bank_number]
        with open(filename, newline="") as csvfile:
            bank_dict_reader = DictReader(csvfile)
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
    if len(argv) == 0:
        print("csv_loader.py <csv_register_map>.csv [--pickle]")
    filename = argv[1]
    if not os.path.exists(filename):
        raise AttributeError("CSV file %s cannot be found"%filename)

    loader = CSVRegisterMapLoader(csv_file=filename)
    if len(argv) == 3 and "--pickle" in argv:
        import pickle
        pickle_name = filename.split(".")[0]+".pickle"
        with open(pickle_name, "wb") as f:
            pickle.dump(loader.map, f)
