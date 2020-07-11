from sys import argv
import json
class FixedDict:
    def __init__(self, broken_dict):
        self._dict = broken_dict

    def __getitem__(self, key):
        if isinstance(key, int):
            val = self._dict[str(key)]
            if isinstance(val, dict):
                return FixedDict(val)
            return self._dict[str(key)]
        return self._dict[key]

    def __setitem__(self, key, value):
        if isinstance(key, int):
            self._dict[str(key)] = value
        self._dict[key] = value
    def __str__(self):
        return str(self._dict)

    def keys(self):
        return [int(i) for i in self._dict.keys()]

from register_decoder.map_loader import RegisterMapLoader
class JSONRegisterMapLoader(RegisterMapLoader):
    def __init__(self, json_map_file):
        super().__init__(map_source=json_map_file)

    def load_map(self):
        loaded_dict = json.load(open(self.map_source))
        fixed_map = FixedDict(loaded_dict)
        self._map = fixed_map
    @property
    def map(self):
        """The object representing the register map"""
        return self._map

if __name__ == "__main__":
    import pprint
    loader = JSONRegisterMapLoader(argv[1])
    pprint.pprint(loader.map, width=30)
