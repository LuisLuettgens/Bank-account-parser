import json
import helper
import parameters as pm


class Database:
    def __init__(self, path: str):
        print(pm.layer_prefix+'Loading new database...')
        helper.is_valid_json_file(path)
        with open(path) as f:
            self.data = json.load(f)
        self.labels = list(self.data.keys())
