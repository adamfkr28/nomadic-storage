from flask import Flask, render_template_string, request, send_file, jsonify
import os
import random
import threading
import time
from network_node import NetworkNode
from client import simpan_ke_node, ambil_dari_node
from sharding import pecah_file, gabung_shard
from crypto import derive_key_from_password

app = Flask(__name__)

# ============================================================
# STATE GLOBAL
# ============================================================
JUMLAH_NODE = 5
JUMLAH_SHARD = 5
REPLIKASI = 3
HOST = "127.0.0.1"
PORT_AWAL = 5001

nodes = []
node_dict = {}
lokasi_shard = {}
file_terakhir = None
salt_terakhir = None

def init_nodes():
    global nodes, node_dict
    for i in range(JUMLAH_NODE):
        node_id = f"node-{i+1}"
        port = PORT_AWAL + i
        node = NetworkNode(node_id, HOST, port)
        nodes.append(node)
        node_dict[node_id] = (HOST, port)
        threading.Thread(target=node.start_server, daemon=True).start()
    time.sleep(2)

# ============================================================
# HTML TEMPLATE
# ============================================================
HTML = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nomadic Storage</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            --bg: #f7f8fa;
            --card: #ffffff;
            --border: #e5e7eb;
            --text: #1f2937;
            --text-muted: #6b7280;
            --accent: #2563eb;
            --accent-hover: #1d4ed8;
            --success: #16a34a;
            --danger: #dc2626;
            --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 40px 20px;
            min-height: 100vh;
        }

        .container { max-width: 900px; margin: 0 auto; }

        header {
            margin-bottom: 32px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border);
        }

        h1 {
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 4px;
        }

        .subtitle {
            color: var(--text-muted);
            font-size: 0.95rem;
        }

        .card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 24px;
            margin-bottom: 16px;
            box-shadow: var(--shadow);
        }

        .card h2 {
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 16px;
        }

        .node-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 8px;
        }

        .node {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            font-size: 0.8rem;
            transition: all 0.15s;
        }

        .node .node-name {
            font-weight: 600;
            color: var(--text);
            font-size: 0.85rem;
        }

        .node .node-status {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success);
            margin: 6px 0;
        }

        .node.mati .node-status {
            background: var(--danger);
        }

        .node .node-port {
            color: var(--text-muted);
            font-size: 0.75rem;
            font-family: 'SF Mono', Monaco, monospace;
        }

        input[type="file"],
        input[type="password"],
        input[type="text"] {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid var(--border);
            border-radius: 8px;
            font-size: 0.9rem;
            font-family: inherit;
            background: var(--card);
            color: var(--text);
            margin-bottom: 10px;
            transition: border-color 0.15s;
        }

        input:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
        }

        input[type="file"] {
            padding: 8px;
            cursor: pointer;
        }

        button {
            background: var(--accent);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.15s;
            font-family: inherit;
        }

        button:hover:not(:disabled) { background: var(--accent-hover); }

        button:disabled {
            background: var(--text-muted);
            cursor: not-allowed;
            opacity: 0.6;
        }

        .log {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 14px;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
            font-size: 0.8rem;
            color: var(--text-muted);
            max-height: 220px;
            overflow-y: auto;
            white-space: pre-wrap;
            line-height: 1.5;
        }

        .log-entry { padding: 2px 0; }
        .log-entry.ok { color: var(--success); }
        .log-entry.err { color: var(--danger); }

        .status-bar {
            display: flex;
            gap: 20px;
            font-size: 0.85rem;
            color: var(--text-muted);
            padding-top: 16px;
            border-top: 1px solid var(--border);
            margin-top: 16px;
        }

        .status-bar strong { color: var(--text); }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Nomadic Storage</h1>
            <p class="subtitle">Penyimpanan terdistribusi &middot; sharding &middot; replikasi &middot; enkripsi AES-256-GCM</p>
        </header>

        <div class="card">
            <h2>Status Node</h2>
            <div class="node-grid" id="node-grid"></div>
            <div class="status-bar">
                <span>Hidup: <strong id="stat-hidup">-</strong></span>
                <span>Total: <strong id="stat-total">-</strong></span>
            </div>
        </div>

        <div class="card">
            <h2>Upload File</h2>
            <input type="file" id="file-input">
            <input type="password" id="password-input" placeholder="Password enkripsi">
            <button onclick="uploadFile()" id="upload-btn">Upload &amp; Sebar</button>
        </div>

        <div class="card">
            <h2>Download File</h2>
            <input type="password" id="download-password" placeholder="Password dekripsi">
            <button onclick="downloadFile()" id="download-btn">Rekonstruksi &amp; Download</button>
        </div>

        <div class="card">
            <h2>Log</h2>
            <div class="log" id="log">Menunggu aktivitas...</div>
        </div>
    </div>

    <script>
        function log(msg, type = '') {
            const el = document.getElementById('log');
            if (el.textContent === 'Menunggu aktivitas...') el.textContent = '';
            const line = document.createElement('div');
            line.className = 'log-entry ' + type;
            line.textContent = msg;
            el.appendChild(line);
            el.scrollTop = el.scrollHeight;
        }

        async function refreshNodes() {
            try {
                const res = await fetch('/api/nodes');
                const data = await res.json();
                const grid = document.getElementById('node-grid');
                grid.innerHTML = '';
                let hidup = 0;
                const total = Object.keys(data).length;
                for (const [id, info] of Object.entries(data)) {
                    if (info.hidup) hidup++;
                    const div = document.createElement('div');
                    div.className = 'node' + (info.hidup ? '' : ' mati');
                    div.innerHTML = `
                        <div class="node-name">${id}</div>
                        <div class="node-status"></div>
                        <div class="node-port">:${info.port}</div>
                    `;
                    grid.appendChild(div);
                }
                document.getElementById('stat-hidup').textContent = hidup;
                document.getElementById('stat-total').textContent = total;
            } catch (e) {}
        }

        async function uploadFile() {
            const fileInput = document.getElementById('file-input');
            const password = document.getElementById('password-input').value;
            if (!fileInput.files.length) { alert('Pilih file dulu.'); return; }
            if (!password) { alert('Masukin password.'); return; }

            const btn = document.getElementById('upload-btn');
            btn.disabled = true;
            btn.textContent = 'Uploading...';
            log('Upload: ' + fileInput.files[0].name);

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('password', password);

            try {
                const res = await fetch('/api/upload', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.status === 'ok') {
                    log(`Selesai: ${data.ukuran} byte, ${data.shard} shard, replikasi ${data.replikasi}x`, 'ok');
                    alert('File berhasil di-upload dan disebar.');
                } else {
                    log('Gagal: ' + data.pesan, 'err');
                    alert('Gagal: ' + data.pesan);
                }
            } catch (e) {
                log('Error: ' + e, 'err');
            }

            btn.disabled = false;
            btn.textContent = 'Upload & Sebar';
            refreshNodes();
        }

        async function downloadFile() {
            const password = document.getElementById('download-password').value;
            if (!password) { alert('Masukin password.'); return; }

            const btn = document.getElementById('download-btn');
            btn.disabled = true;
            btn.textContent = 'Rekonstruksi...';
            log('Rekonstruksi file...');

            try {
                const res = await fetch('/api/download', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({password: password})
                });

                if (res.ok) {
                    const blob = await res.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'file_hasil.txt';
                    a.click();
                    log('File berhasil direkonstruksi.', 'ok');
                } else {
                    const data = await res.json();
                    log('Gagal: ' + data.pesan, 'err');
                    alert('Gagal: ' + data.pesan);
                }
            } catch (e) {
                log('Error: ' + e, 'err');
            }

            btn.disabled = false;
            btn.textContent = 'Rekonstruksi & Download';
        }

        setInterval(refreshNodes, 2000);
        refreshNodes();
    </script>
</body>
</html>
"""

# ============================================================
# ROUTES
# ============================================================
@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/api/nodes')
def api_nodes():
    result = {}
    for node in nodes:
        result[node.node_id] = {
            "hidup": node.running,
            "port": node.port
        }
    return jsonify(result)

@app.route('/api/upload', methods=['POST'])
def api_upload():
    global lokasi_shard, file_terakhir, salt_terakhir
    file = request.files.get('file')
    password = request.form.get('password')

    if not file or not password:
        return jsonify({"status": "gagal", "pesan": "File atau password kosong"})

    file_bytes = file.read()
    with open("temp_upload.txt", "wb") as f:
        f.write(file_bytes)

    # Turunin kunci + SIMPEN SALT
    key, salt = derive_key_from_password(password)
    salt_terakhir = salt

    shards = pecah_file("temp_upload.txt", JUMLAH_SHARD, key)

    node_ids = list(node_dict.keys())
    lokasi_shard = {}
    for i, shard in enumerate(shards):
        shard_id = f"shard-{i}"
        node_pilihan = random.sample(node_ids, REPLIKASI)
        lokasi_shard[shard_id] = node_pilihan
        for nid in node_pilihan:
            host, port = node_dict[nid]
            simpan_ke_node(host, port, shard_id, shard)

    file_terakhir = file.filename

    return jsonify({
        "status": "ok",
        "file": file.filename,
        "ukuran": len(file_bytes),
        "shard": JUMLAH_SHARD,
        "replikasi": REPLIKASI,
        "lokasi": lokasi_shard
    })

@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.get_json()
    password = data.get('password')

    if not password:
        return jsonify({"status": "gagal", "pesan": "Password kosong"}), 400

    if not lokasi_shard or salt_terakhir is None:
        return jsonify({"status": "gagal", "pesan": "Belum ada file yang di-upload"}), 400

    # PAKE SALT YANG SAMA KAYAK PAS UPLOAD
    key, _ = derive_key_from_password(password, salt_terakhir)

    shards_ditemukan = []
    for i in range(JUMLAH_SHARD):
        shard_id = f"shard-{i}"
        ketemu = False
        for nid in lokasi_shard[shard_id]:
            host, port = node_dict[nid]
            hasil = ambil_dari_node(host, port, shard_id)
            if hasil.get("status") == "ok":
                shards_ditemukan.append(bytes.fromhex(hasil["data"]))
                ketemu = True
                break
        if not ketemu:
            shards_ditemukan.append(None)

    try:
        gabung_shard(shards_ditemukan, "temp_download.txt", key)
    except Exception as e:
        return jsonify({"status": "gagal", "pesan": f"Gagal dekripsi: {type(e).__name__}"}), 400

    return send_file("temp_download.txt", as_attachment=True, download_name="file_hasil.txt")

# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("=" * 70)
    print("  NOMADIC STORAGE - WEB UI")
    print("=" * 70)
    print("\n  Nyalain node...")
    init_nodes()
    print(f"  {JUMLAH_NODE} node jalan di port {PORT_AWAL}-{PORT_AWAL + JUMLAH_NODE - 1}")
    print("\n  Buka browser: http://127.0.0.1:8080")
    print("=" * 70 + "\n")
    app.run(host="0.0.0.0", port=8080, debug=False)