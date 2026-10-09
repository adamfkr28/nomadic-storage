import os
import random
import shutil
import time
from network_node import NetworkNode
from client import simpan_ke_node, ambil_dari_node, ping_node
from sharding import pecah_file, gabung_shard
from crypto import generate_key
from discovery import DiscoveryService

# ============================================================
# KONFIGURASI
# ============================================================
JUMLAH_NODE = 5
JUMLAH_SHARD = 5
REPLIKASI = 3
NODE_MATI = 2
HOST = "127.0.0.1"
PORT_AWAL = 5001
DISCOVERY_PORT = 9999

# Bersihin storage lama
if os.path.exists("storage"):
    shutil.rmtree("storage")

# Bikin node + discovery
nodes = []
discoveries = []
for i in range(JUMLAH_NODE):
    node_id = f"node-{i+1}"
    port = PORT_AWAL + i
    node = NetworkNode(node_id, HOST, port)
    nodes.append(node)

    disc = DiscoveryService(node_id, HOST, port, DISCOVERY_PORT)
    discoveries.append(disc)

# Jalanin server + discovery
print("--- START SERVER + DISCOVERY ---")
import threading
for node in nodes:
    t = threading.Thread(target=node.start_server, daemon=True)
    t.start()

for disc in discoveries:
    disc.start()

# Tunggu discovery selesai (node saling kenal)
print("\nTunggu 6 detik biar node saling kenal...")
time.sleep(6)

# Cek siapa kenal siapa
print("\n--- PETA DISCOVERY ---")
for disc in discoveries:
    peers = disc.get_peers()
    print(f"[{disc.node_id}] kenal {len(peers)} node: {list(peers.keys())}")

# ============================================================
# FASE 1: SEBAR
# ============================================================
key = generate_key()
print(f"\nKunci enkripsi: {key.hex()}\n")

with open("file_asli.txt", "wb") as f:
    f.write(b"Ini isi file rahasia gue. " * 5000)

print(f"File asli: {os.path.getsize('file_asli.txt')} bytes")
print(f"Node: {JUMLAH_NODE} | Shard: {JUMLAH_SHARD} | Replikasi: {REPLIKASI}x\n")

shards = pecah_file("file_asli.txt", JUMLAH_SHARD, key)

print(f"--- FASE SEBAR (PAKE DISCOVERY) ---")
lokasi_shard = {}
node_ids = [n.node_id for n in nodes]

for i, shard in enumerate(shards):
    shard_id = f"shard-{i}"
    node_pilihan = random.sample(node_ids, REPLIKASI)
    lokasi_shard[shard_id] = node_pilihan
    for nid in node_pilihan:
        # Cari alamat node dari discovery, bukan dari dict manual
        alamat = None
        for disc in discoveries:
            peers = disc.get_peers()
            if nid in peers:
                alamat = peers[nid]
                break
        if alamat is None:
            # Fallback ke alamat default
            idx = node_ids.index(nid)
            alamat = (HOST, PORT_AWAL + idx)

        host, port = alamat
        hasil = simpan_ke_node(host, port, shard_id, shard)
        if hasil.get("status") == "ok":
            print(f"  {shard_id} -> {nid} ({host}:{port}) OK")
        else:
            print(f"  {shard_id} -> {nid} GAGAL: {hasil.get('pesan')}")

print("\nPeta lokasi shard:")
for shard_id, nids in lokasi_shard.items():
    print(f"  {shard_id} -> {nids}")

# ============================================================
# FASE 2: NODE MATI
# ============================================================
print(f"\n--- FASE {NODE_MATI} NODE MATI ---")
node_mati = random.sample(nodes, NODE_MATI)
node_mati_ids = [n.node_id for n in node_mati]
print(f"Node MATI: {node_mati_ids}")
for n in node_mati:
    n.stop_server()
    for disc in discoveries:
        if disc.node_id == n.node_id:
            disc.stop()
    print(f"  {n.node_id} dimatiin.")

time.sleep(1)

# ============================================================
# FASE 3: REKONSTRUKSI
# ============================================================
print("\n--- FASE REKONSTRUKSI (PAKE DISCOVERY) ---")
shards_ditemukan = []
for i in range(JUMLAH_SHARD):
    shard_id = f"shard-{i}"
    ketemu = False
    for nid in lokasi_shard[shard_id]:
        if nid in node_mati_ids:
            continue
        # Cari alamat dari discovery
        alamat = None
        for disc in discoveries:
            peers = disc.get_peers()
            if nid in peers:
                alamat = peers[nid]
                break
        if alamat is None:
            idx = node_ids.index(nid)
            alamat = (HOST, PORT_AWAL + idx)

        host, port = alamat
        hasil = ambil_dari_node(host, port, shard_id)
        if hasil.get("status") == "ok":
            data = bytes.fromhex(hasil["data"])
            shards_ditemukan.append(data)
            ketemu = True
            print(f"  {shard_id} diambil dari {nid}")
            break
    if not ketemu:
        shards_ditemukan.append(None)
        print(f"  {shard_id} GAK KETEMU")

try:
    gabung_shard(shards_ditemukan, "file_hasil.txt", key)
    with open("file_asli.txt", "rb") as f1, open("file_hasil.txt", "rb") as f2:
        if f1.read() == f2.read():
            print("\nSUKSES: File identik dengan aslinya!")
        else:
            print("\nGAGAL: File berbeda!")
except ValueError as e:
    print(f"\nGAGAL: {e}")

# Shutdown
print("\n--- SHUTDOWN ---")
for node in nodes:
    node.stop_server()
for disc in discoveries:
    disc.stop()
print("Semua server + discovery dimatiin.")