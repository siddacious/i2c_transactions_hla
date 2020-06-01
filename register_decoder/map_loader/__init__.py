class RegisterMapLoader:
    def __init__(self, map_source=None):
        self.map_source = map_source
        self._map = None
        self.load_map()

    def load_map(self):
        if self.map_source is None:
            raise AttributeError("Base Class", self.__name__, "cannot be instantiated directly")
    @property
    def map(self):
        """The object representing the register map"""
        return self._map