import os
import random
import shutil
import threading
import time
from network_node import NetworkNode
from client import simpan_ke_node, ambil_dari_node
from sharding import pecah_file, gabung_shard
from crypto import derive_key_from_password
from discovery import DiscoveryService
from visualizer import Visualizer

# ============================================================
# KONFIGURASI
# ============================================================
JUMLAH_NODE = 5
JUMLAH_SHARD = 5
REPLIKASI = 3
HOST = "127.0.0.1"
PORT_AWAL = 5001
DISCOVERY_PORT = 9999

# ============================================================
# INPUT PASSWORD
# ============================================================
print("=" * 70)
print("  NOMADIC STORAGE - SETUP")
print("=" * 70)

password = input("  Masukin password: ")
print(f"\n  Password: {'*' * len(password)} ({len(password)} karakter)")

# Turunin kunci dari password
key, salt = derive_key_from_password(password)
print(f"  Salt (acak, gak perlu dirahasiakan): {salt.hex()}")
print(f"  Kunci enkripsi (dari password): {key.hex()[:32]}...")
print("=" * 70)

input("\n  Tekan Enter buat mulai...")

# Bersihin storage lama
if os.path.exists("storage"):
    shutil.rmtree("storage")

# Bikin node
nodes = []
for i in range(JUMLAH_NODE):
    node_id = f"node-{i+1}"
    port = PORT_AWAL + i
    node = NetworkNode(node_id, HOST, port)
    nodes.append(node)

# Bikin discovery
discoveries = []
for i, node in enumerate(nodes):
    disc = DiscoveryService(node.node_id, HOST, PORT_AWAL + i, DISCOVERY_PORT)
    discoveries.append(disc)

# Bikin visualizer
viz = Visualizer(nodes, {})

# Jalanin server + discovery
viz.render("START", "Nyalain server + discovery...")
for node in nodes:
    threading.Thread(target=node.start_server, daemon=True).start()
for disc in discoveries:
    disc.start()

time.sleep(5)

# Update lokasi shard di visualizer
node_dict = {n.node_id: (HOST, n.port) for n in nodes}

# Bikin file
with open("file_asli.txt", "wb") as f:
    f.write(b"Ini isi file rahasia gue. " * 5000)

shards = pecah_file("file_asli.txt", JUMLAH_SHARD, key)

# ============================================================
# FASE 1: SEBAR
# ============================================================
node_ids = list(node_dict.keys())
lokasi_shard = {}

for i, shard in enumerate(shards):
    shard_id = f"shard-{i}"
    node_pilihan = random.sample(node_ids, REPLIKASI)
    lokasi_shard[shard_id] = node_pilihan

    for nid in node_pilihan:
        host, port = node_dict[nid]
        simpan_ke_node(host, port, shard_id, shard)

    viz.lokasi_shard = lokasi_shard.copy()
    viz.render("SEBAR", f"{shard_id} -> {node_pilihan}")
    time.sleep(0.8)

# ============================================================
# FASE 2: NORMAL
# ============================================================
viz.lokasi_shard = lokasi_shard
viz.render("NORMAL", "Semua node hidup, semua shard tersedia")
time.sleep(2)

# ============================================================
# FASE 3: NODE MATI
# ============================================================
node_mati_ids = []
urutan_mati = random.sample(nodes, 2)

for node in urutan_mati:
    node.stop_server()
    for disc in discoveries:
        if disc.node_id == node.node_id:
            disc.stop()
    node_mati_ids.append(node.node_id)
    viz.node_mati_ids = node_mati_ids.copy()
    viz.render("NODE MATI", f"{node.node_id} mati!")
    time.sleep(1.5)

# ============================================================
# FASE 4: REKONSTRUKSI PAKAI PASSWORD
# ============================================================
viz.render("REKONSTRUKSI", "Masukin password buat dekripsi...")
time.sleep(2)

print("\n" + "=" * 70)
print("  REKONSTRUKSI FILE")
print("=" * 70)

password_input = input("  Masukin password (sama kayak tadi): ")

# Turunin ulang kunci dari password + salt yang sama
key_input, _ = derive_key_from_password(password_input, salt)

# Cek kunci bener apa salah
if key_input != key:
    print("\n  ❌ PASSWORD SALAH! File gak bisa didekripsi.")
    print("=" * 70)
    for node in nodes:
        node.stop_server()
    for disc in discoveries:
        disc.stop()
    exit(1)

print("  ✅ Password bener! Lanjut rekonstruksi...")
print("=" * 70 + "\n")

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
            viz.render("REKONSTRUKSI", f"{shard_id} diambil dari {nid}")
            time.sleep(0.6)
            break
    if not ketemu:
        shards_ditemukan.append(None)
        viz.render("REKONSTRUKSI", f"{shard_id} GAK KETEMU!")
        time.sleep(0.6)

# ============================================================
# FASE 5: HASIL
# ============================================================
try:
    gabung_shard(shards_ditemukan, "file_hasil.txt", key)
    with open("file_asli.txt", "rb") as f1, open("file_hasil.txt", "rb") as f2:
        if f1.read() == f2.read():
            viz.render("SELESAI", "SUKSES: File identik dengan aslinya!")
        else:
            viz.render("SELESAI", "GAGAL: File berbeda!")
except ValueError as e:
    viz.render("SELESAI", f"GAGAL: {e}")

time.sleep(3)

# Shutdown
for node in nodes:
    node.stop_server()
for disc in discoveries:
    disc.stop()
print("\nSemua server dimatiin.")