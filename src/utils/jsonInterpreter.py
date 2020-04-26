import json
import helper


class Database:
    def __init__(self, path: str):
        print("Database constructor!")
        helper.is_valid_json_file(path)
        with open(path) as f:
            self.data = data = json.load(f)
        self.labels = list(self.data.keys())
