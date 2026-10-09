import os
import hashlib
import json

class Node:
    def __init__(self, node_id):
        self.node_id = node_id
        self.storage_dir = f"storage/{node_id}"
        os.makedirs(self.storage_dir, exist_ok=True)
        self.index_file = f"{self.storage_dir}/index.json"
        self.load_index()

    def load_index(self):
        if os.path.exists(self.index_file):
            with open(self.index_file, "r") as f:
                self.index = json.load(f)
        else:
            self.index = {}

    def save_index(self):
        with open(self.index_file, "w") as f:
            json.dump(self.index, f)

    def simpan_shard(self, shard_id, data):
        shard_path = f"{self.storage_dir}/{shard_id}.bin"
        with open(shard_path, "wb") as f:
            f.write(data)
        self.index[shard_id] = hashlib.sha256(data).hexdigest()
        self.save_index()
        print(f"[{self.node_id}] Shard {shard_id} disimpan.")

    def ambil_shard(self, shard_id):
        shard_path = f"{self.storage_dir}/{shard_id}.bin"
        if not os.path.exists(shard_path):
            return None
        with open(shard_path, "rb") as f:
            data = f.read()
        hash_sekarang = hashlib.sha256(data).hexdigest()
        if hash_sekarang != self.index.get(shard_id):
            print(f"[{self.node_id}] WARNING: Shard {shard_id} korup!")
            return None
        return data

    def masih_hidup(self):
        return True