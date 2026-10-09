import socket
import json
import threading
import time

class DiscoveryService:
    def __init__(self, node_id, host, port, discovery_port):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.discovery_port = discovery_port
        self.peers = {}  # {node_id: (host, port)}
        self.running = False
        self.sock = None

    def start(self):
        """Jalanin discovery service di background thread."""
        self.running = True
        thread = threading.Thread(target=self._listen, daemon=True)
        thread.start()
        thread2 = threading.Thread(target=self._announce_loop, daemon=True)
        thread2.start()

    def _listen(self):
        """Dengerin broadcast dari node lain."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", self.discovery_port))
        self.sock.settimeout(1)

        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                pesan = json.loads(data.decode())
                node_id = pesan.get("node_id")
                host = pesan.get("host")
                port = pesan.get("port")

                if node_id and node_id != self.node_id:
                    if node_id not in self.peers:
                        print(f"[{self.node_id}] Ketemu node baru: {node_id} di {host}:{port}")
                    self.peers[node_id] = (host, port)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[{self.node_id}] Discovery error: {e}")

    def _announce_loop(self):
        """Teriak ke jaringan tiap 2 detik."""
        announce_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        announce_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while self.running:
            try:
                pesan = json.dumps({
                    "node_id": self.node_id,
                    "host": self.host,
                    "port": self.port
                }).encode()
                announce_sock.sendto(pesan, ("255.255.255.255", self.discovery_port))
                time.sleep(2)
            except Exception as e:
                if self.running:
                    print(f"[{self.node_id}] Announce error: {e}")
                break

    def stop(self):
        self.running = False
        if self.sock:
            self.sock.close()

    def get_peers(self):
        """Ambil daftar node yang udah dikenal."""
        return dict(self.peers)