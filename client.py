import socket
import json
import struct

def kirim_perintah(host, port, perintah):
    """Kirim perintah ke node lewat socket dengan protokol length-prefix."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((host, port))

        # Serialize perintah ke JSON bytes
        payload = json.dumps(perintah).encode()

        # Kirim dulu ukuran payload (4 byte, big-endian)
        sock.sendall(struct.pack(">I", len(payload)))

        # Baru kirim payload-nya
        sock.sendall(payload)

        # Terima response: baca 4 byte ukuran dulu
        ukuran_bytes = b""
        while len(ukuran_bytes) < 4:
            chunk = sock.recv(4 - len(ukuran_bytes))
            if not chunk:
                break
            ukuran_bytes += chunk

        if len(ukuran_bytes) < 4:
            sock.close()
            return {"status": "error", "pesan": "response kosong"}

        ukuran = struct.unpack(">I", ukuran_bytes)[0]

        # Baca response sebanyak ukuran
        response_bytes = b""
        while len(response_bytes) < ukuran:
            chunk = sock.recv(min(65536, ukuran - len(response_bytes)))
            if not chunk:
                break
            response_bytes += chunk

        sock.close()
        return json.loads(response_bytes.decode())

    except Exception as e:
        return {"status": "error", "pesan": str(e)}

def simpan_ke_node(host, port, shard_id, data):
    perintah = {"aksi": "simpan", "shard_id": shard_id, "data": data.hex()}
    return kirim_perintah(host, port, perintah)

def ambil_dari_node(host, port, shard_id):
    perintah = {"aksi": "ambil", "shard_id": shard_id}
    return kirim_perintah(host, port, perintah)

def ping_node(host, port):
    perintah = {"aksi": "ping"}
    return kirim_perintah(host, port, perintah)