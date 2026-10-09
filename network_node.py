import socket
import threading
import json
import os
import hashlib
import struct

class NetworkNode:
    def __init__(self, node_id, host, port):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.storage_dir = f"storage/{node_id}"
        os.makedirs(self.storage_dir, exist_ok=True)
        self.index_file = f"{self.storage_dir}/index.json"
        self.load_index()
        self.server_socket = None
        self.running = False

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

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        print(f"[{self.node_id}] Server jalan di {self.host}:{self.port}")
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
            except:
                break

    def handle_client(self, client_socket):
        try:
            ukuran_bytes = b""
            while len(ukuran_bytes) < 4:
                chunk = client_socket.recv(4 - len(ukuran_bytes))
                if not chunk:
                    return
                ukuran_bytes += chunk

            ukuran = struct.unpack(">I", ukuran_bytes)[0]

            request_bytes = b""
            while len(request_bytes) < ukuran:
                chunk = client_socket.recv(min(65536, ukuran - len(request_bytes)))
                if not chunk:
                    break
                request_bytes += chunk

            perintah = json.loads(request_bytes.decode())
            aksi = perintah.get("aksi")

            if aksi == "simpan":
                shard_id = perintah["shard_id"]
                data = bytes.fromhex(perintah["data"])
                self.simpan_shard(shard_id, data)
                response = {"status": "ok"}

            elif aksi == "ambil":
                shard_id = perintah["shard_id"]
                data = self.ambil_shard(shard_id)
                if data:
                    response = {"status": "ok", "data": data.hex()}
                else:
                    response = {"status": "gagal", "pesan": "shard gak ada"}

            elif aksi == "ping":
                response = {"status": "ok", "node_id": self.node_id}

            else:
                response = {"status": "gagal", "pesan": "aksi gak dikenal"}

            response_bytes = json.dumps(response).encode()
            client_socket.sendall(struct.pack(">I", len(response_bytes)))
            client_socket.sendall(response_bytes)

        except Exception as e:
            try:
                response_bytes = json.dumps({"status": "error", "pesan": str(e)}).encode()
                client_socket.sendall(struct.pack(">I", len(response_bytes)))
                client_socket.sendall(response_bytes)
            except:
                pass
        finally:
            client_socket.close()

    def stop_server(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()