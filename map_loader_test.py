import os

class TestClass:
    def __init__(self, map_path):
        self.csv_register_map_path = map_path

        self.map_loader = None
        self._load_register_map()
        print("map_loader:", self.map_loader)
        print("type(map_loader.map)", type(self.map_loader.map))
        # apolgies to demeter
        print("map keys:", self.map_loader.map.keys())

    def _load_register_map(self):
        print("CSV path setting:", self.csv_register_map_path, type(self.csv_register_map_path))
        if self.csv_register_map_path:
            if not os.path.exists(self.csv_register_map_path):
                raise FileNotFoundError("no file found at %s"%self.csv_register_map_path)

            from csv_loader import CSVRegisterMapLoader
            self.map_loader = CSVRegisterMapLoader([self.csv_register_map_path])

if __name__ == "__main__":
    map_path = "/Users/bs/dev/tooling/i2c_txns/maps/as7341_map_rewrite.csv"
    print("file path:", map_path)
    print("file exists?", os.path.exists(map_path))
    print("creating TestClass instance")
    tester = TestClass(map_path)