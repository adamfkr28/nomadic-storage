import os
import random
import shutil
from node import Node
from sharding import pecah_file, gabung_shard
from crypto import generate_key

# ============================================================
# KONFIGURASI
# ============================================================
JUMLAH_NODE = 5
JUMLAH_SHARD = 5
REPLIKASI = 3
NODE_MATI = 2

# Bersihin storage lama
if os.path.exists("storage"):
    shutil.rmtree("storage")

# Bikin node simulasi
nodes = [Node(f"node-{i}") for i in range(1, JUMLAH_NODE + 1)]
node_dict = {n.node_id: n for n in nodes}

# Bikin kunci enkripsi
key = generate_key()
print(f"Kunci enkripsi (simpan baik-baik!): {key.hex()}\n")

# Bikin file dummy
with open("file_asli.txt", "wb") as f:
    f.write(b"Ini isi file rahasia gue. " * 5000)

print(f"File asli: {os.path.getsize('file_asli.txt')} bytes")
print(f"Node: {JUMLAH_NODE} | Shard: {JUMLAH_SHARD} | Replikasi: {REPLIKASI}x\n")

# Pecah + enkripsi shard
shards = pecah_file("file_asli.txt", JUMLAH_SHARD, key)

# ============================================================
# FASE 1: SEBAR SHARD
# ============================================================
print(f"--- FASE SEBAR (REPLIKASI {REPLIKASI}x + ENKRIPSI) ---")
lokasi_shard = {}
for i, shard in enumerate(shards):
    shard_id = f"shard-{i}"
    node_pilihan = random.sample(nodes, REPLIKASI)
    lokasi_shard[shard_id] = [n.node_id for n in node_pilihan]
    for node in node_pilihan:
        node.simpan_shard(shard_id, shard)

print("\nPeta lokasi shard:")
for shard_id, node_ids in lokasi_shard.items():
    print(f"  {shard_id} -> {node_ids}")

# ============================================================
# FASE 2: BUKTI ENKRIPSI
# ============================================================
print("\n--- BUKTI ENKRIPSI ---")
contoh_node = nodes[0]
contoh_shard = list(contoh_node.index.keys())[0]
path_contoh = f"{contoh_node.storage_dir}/{contoh_shard}.bin"
with open(path_contoh, "rb") as f:
    isi = f.read(64)
print(f"Isi shard {contoh_shard} di {contoh_node.node_id} (64 byte pertama):")
print(f"  {isi.hex()}")
print("  ^ Ini data acak, gak bisa dibaca tanpa kunci.\n")

# ============================================================
# FASE 3: NODE MATI
# ============================================================
print(f"--- FASE {NODE_MATI} NODE MATI ---")
node_mati = random.sample(nodes, NODE_MATI)
node_mati_ids = [n.node_id for n in node_mati]
print(f"Node MATI: {node_mati_ids}\n")

# ============================================================
# FASE 4: DETEKSI KORUP
# ============================================================
print("--- FASE DETEKSI KORUP ---")
node_hidup = [n for n in nodes if n.node_id not in node_mati_ids]
if node_hidup:
    korban = random.choice(node_hidup)
    shard_korup = random.choice(list(korban.index.keys()))
    path_korup = f"{korban.storage_dir}/{shard_korup}.bin"
    with open(path_korup, "wb") as f:
        f.write(b"INI SUDAH DIUBAH ORANG!")
    print(f"Shard {shard_korup} di {korban.node_id} sengaja dirusak.\n")

# ============================================================
# FASE 5: SELF-HEALING
# ============================================================
print("--- FASE SELF-HEALING ---")
for shard_id, node_ids_di_peta in lokasi_shard.items():
    node_tersedia = [nid for nid in node_ids_di_peta if nid not in node_mati_ids]
    shard_ok = False
    for nid in node_tersedia:
        data = node_dict[nid].ambil_shard(shard_id)
        if data is not None:
            shard_ok = True
            break
    if not shard_ok:
        print(f"  {shard_id} HILANG dari semua node hidup -> butuh replikasi ulang")
        data_shard = None
        for nid in node_ids_di_peta:
            if nid in node_mati_ids:
                continue
            data_shard = node_dict[nid].ambil_shard(shard_id)
            if data_shard:
                break
        if data_shard:
            kandidat = [n for n in node_hidup if shard_id not in n.index]
            if kandidat:
                target = random.choice(kandidat)
                target.simpan_shard(shard_id, data_shard)
                print(f"    -> Direplikasi ulang ke {target.node_id}")
    else:
        jumlah_hidup = len(node_tersedia)
        if jumlah_hidup < REPLIKASI:
            data_shard = node_dict[node_tersedia[0]].ambil_shard(shard_id)
            if data_shard:
                kandidat = [n for n in node_hidup if shard_id not in n.index]
                if kandidat:
                    target = random.choice(kandidat)
                    target.simpan_shard(shard_id, data_shard)
                    print(f"  {shard_id} kurang replika ({jumlah_hidup}/{REPLIKASI}) -> tambah ke {target.node_id}")

print()

# ============================================================
# FASE 6: REKONSTRUKSI
# ============================================================
print("--- FASE REKONSTRUKSI (DEKRIPSI) ---")
shards_ditemukan = []
for i in range(JUMLAH_SHARD):
    shard_id = f"shard-{i}"
    ketemu = False
    for node in nodes:
        if node.node_id in node_mati_ids:
            continue
        data = node.ambil_shard(shard_id)
        if data is not None:
            shards_ditemukan.append(data)
            ketemu = True
            break
    if not ketemu:
        shards_ditemukan.append(None)

try:
    gabung_shard(shards_ditemukan, "file_hasil.txt", key)
    with open("file_asli.txt", "rb") as f1, open("file_hasil.txt", "rb") as f2:
        if f1.read() == f2.read():
            print("SUKSES: File identik dengan aslinya!")
        else:
            print("GAGAL: File berbeda!")
except ValueError as e:
    print(f"GAGAL: {e}")

# ============================================================
# FASE 7: BUKTI KUNCI SALAH
# ============================================================
print("\n--- BUKTI: KUNCI SALAH GAGAL DEKRIPSI ---")
kunci_salah = generate_key()
try:
    gabung_shard(shards_ditemukan, "file_salah.txt", kunci_salah)
    print("WARNING: Kunci salah tapi berhasil? Ada yang aneh.")
except Exception as e:
    print(f"BENAR: Kunci salah ditolak -> {type(e).__name__}")