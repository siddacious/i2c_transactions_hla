from sys import argv
from csv import DictReader
class CSVRegisterMapLoader:
    def __init__(self, csv_files=None, serial_device=None):
        self.map = {0: {}, 1: {}, 2: {}, 3: {}, -1:{127:{'name': 'REG_BANK_SEL', 'address': 127, 0: '', 1: '', 2: '', 3: '', 4: 'USER_BANK[1:0]', 5: 'USER_BANK[1:0]', 6: '', 7: '', 'last_read_value': None}}}
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

    loader = CSVRegisterMapLoader(argv[1:])
    print(loader.map)
