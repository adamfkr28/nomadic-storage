import math
from crypto import encrypt_shard, decrypt_shard

def pecah_file(file_path, jumlah_shard, key):
    with open(file_path, "rb") as f:
        data = f.read()

    ukuran_shard = math.ceil(len(data) / jumlah_shard)
    shards = []

    for i in range(jumlah_shard):
        mulai = i * ukuran_shard
        selesai = mulai + ukuran_shard
        shard = data[mulai:selesai]
        shard_encrypted = encrypt_shard(shard, key)
        shards.append(shard_encrypted)

    return shards

def gabung_shard(shards, output_path, key):
    with open(output_path, "wb") as f:
        for shard in shards:
            if shard is None:
                raise ValueError("Ada shard yang hilang! Gagal rekonstruksi.")
            shard_decrypted = decrypt_shard(shard, key)
            f.write(shard_decrypted)
    print(f"File berhasil direkonstruksi: {output_path}")