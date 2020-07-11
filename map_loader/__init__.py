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

