import json
import os


class DatasetLoader:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.active_dataset = None
        self.cache = {}
        # Try to set default
        datasets = self.list_datasets()
        if datasets:
            self.set_active_dataset(datasets[0]["filename"])

    def list_datasets(self):
        """
        Scans data_dir. Returns list of datasets.
        A dataset can be an MDB file or a Directory (from restored JSONs).
        We favor Directories or MDBs.
        """
        datasets = []
        if not os.path.exists(self.data_dir):
            return []

        for name in os.listdir(self.data_dir):
            path = os.path.join(self.data_dir, name)
            if name.startswith("."):
                continue

            # Criteria: MDB file OR Directory containing .json files
            is_valid = False
            if os.path.isdir(path):
                # Check for json files
                if any(f.endswith(".json") for f in os.listdir(path)):
                    is_valid = True
            elif name.endswith(".mdb"):
                is_valid = True

            if is_valid:
                datasets.append(
                    {
                        "filename": name,
                        "isActive": (self.active_dataset == name),
                        "lastModified": str(int(os.path.getmtime(path))),
                    }
                )
        return datasets

    def set_active_dataset(self, filename):
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Dataset {filename} not found")

        self.active_dataset = filename
        self.cache = {}  # Clear cache
        self._load_data(path)

    def _load_data(self, path):
        # If directory, load JSONs
        if os.path.isdir(path):
            print(f"Loading JSON data from {path}...")
            for f in os.listdir(path):
                if f.endswith(".json"):
                    table_name = f.replace(".json", "")
                    try:
                        with open(os.path.join(path, f)) as json_file:
                            data = json.load(json_file)
                            # Handle different json formats (list vs dict with rows)
                            if isinstance(data, list):
                                self.cache[table_name] = data
                            elif isinstance(data, dict) and "rows" in data:
                                self.cache[table_name] = data["rows"]
                            else:
                                print(f"Warning: Unknown JSON format in {f}")
                    except Exception as e:
                        print(f"Error loading {f}: {e}")
        else:
            print("MDB loading not implemented directly in loader. Use restore_mdb.py first.")
            # In Phase 5, we rely on pre-converted JSONs or implementation in server.py calling mdbtools
            # But server.py uses loader.get_data().
            # If path is MDB, we should probably trigger conversion?
            # For now, assume JSON dirtiest exists.
            pass

    def get_data(self, table_name):
        return self.cache.get(table_name, [])
