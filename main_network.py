import os
import random
import shutil
import threading
import time
from network_node import NetworkNode
from client import simpan_ke_node, ambil_dari_node, ping_node
from sharding import pecah_file, gabung_shard
from crypto import generate_key

# ============================================================
# KONFIGURASI
# ============================================================
JUMLAH_NODE = 5
JUMLAH_SHARD = 5
REPLIKASI = 3
NODE_MATI = 2
HOST = "127.0.0.1"
PORT_AWAL = 5001

# Bersihin storage lama
if os.path.exists("storage"):
    shutil.rmtree("storage")

# Bikin node jaringan
nodes = []
node_dict = {}
for i in range(JUMLAH_NODE):
    node_id = f"node-{i+1}"
    port = PORT_AWAL + i
    node = NetworkNode(node_id, HOST, port)
    nodes.append(node)
    node_dict[node_id] = (HOST, port)

# Jalanin semua server di thread terpisah
print("--- START SERVER ---")
threads = []
for node in nodes:
    t = threading.Thread(target=node.start_server, daemon=True)
    t.start()
    threads.append(t)

time.sleep(1)  # tunggu server siap

# Bikin kunci
key = generate_key()
print(f"\nKunci enkripsi: {key.hex()}\n")

# Bikin file dummy
with open("file_asli.txt", "wb") as f:
    f.write(b"Ini isi file rahasia gue. " * 5000)

print(f"File asli: {os.path.getsize('file_asli.txt')} bytes")
print(f"Node: {JUMLAH_NODE} | Shard: {JUMLAH_SHARD} | Replikasi: {REPLIKASI}x\n")

# Pecah + enkripsi
shards = pecah_file("file_asli.txt", JUMLAH_SHARD, key)

# ============================================================
# FASE 1: SEBAR LEWAT JARINGAN
# ============================================================
print(f"--- FASE SEBAR (LEWAT JARINGAN) ---")
lokasi_shard = {}
node_ids = list(node_dict.keys())

for i, shard in enumerate(shards):
    shard_id = f"shard-{i}"
    node_pilihan = random.sample(node_ids, REPLIKASI)
    lokasi_shard[shard_id] = node_pilihan
    for nid in node_pilihan:
        host, port = node_dict[nid]
        hasil = simpan_ke_node(host, port, shard_id, shard)
        if hasil.get("status") == "ok":
            print(f"  {shard_id} -> {nid} ({host}:{port}) OK")
        else:
            print(f"  {shard_id} -> {nid} GAGAL: {hasil.get('pesan')}")

print("\nPeta lokasi shard:")
for shard_id, nids in lokasi_shard.items():
    print(f"  {shard_id} -> {nids}")

# ============================================================
# FASE 2: PING SEMUA NODE
# ============================================================
print("\n--- PING SEMUA NODE ---")
for node in nodes:
    hasil = ping_node(node.host, node.port)
    print(f"  {node.node_id} ({node.host}:{node.port}) -> {hasil.get('status')}")

# ============================================================
# FASE 3: NODE MATI
# ============================================================
print(f"\n--- FASE {NODE_MATI} NODE MATI ---")
node_mati = random.sample(nodes, NODE_MATI)
node_mati_ids = [n.node_id for n in node_mati]
print(f"Node MATI: {node_mati_ids}")
for n in node_mati:
    n.stop_server()
    print(f"  {n.node_id} dimatiin.")

time.sleep(1)

# ============================================================
# FASE 4: REKONSTRUKSI LEWAT JARINGAN
# ============================================================
print("\n--- FASE REKONSTRUKSI (LEWAT JARINGAN) ---")
shards_ditemukan = []
for i in range(JUMLAH_SHARD):
    shard_id = f"shard-{i}"
    ketemu = False
    for nid in lokasi_shard[shard_id]:
        if nid in node_mati_ids:
            continue
        host, port = node_dict[nid]
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

# Matiin semua server
print("\n--- SHUTDOWN ---")
for node in nodes:
    node.stop_server()
print("Semua server dimatiin.")