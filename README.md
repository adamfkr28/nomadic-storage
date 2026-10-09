# Nomadic Storage

Penyimpanan terdistribusi dari nol — tanpa cloud, tanpa server pusat, tanpa ketergantungan pihak ketiga.

Dibangun dengan Python murni, socket TCP/IP, dan enkripsi AES-256-GCM.

---

## Apa Ini?

Nomadic Storage adalah sistem penyimpanan file terdistribusi yang:

- **Memecah file** jadi beberapa shard (sharding).
- **Menyebar shard** ke beberapa node secara acak.
- **Mereplikasi** setiap shard ke 3 node berbeda.
- **Mengenkripsi** setiap shard dengan AES-256-GCM.
- **Memverifikasi** integritas shard dengan SHA-256.
- **Memulihkan diri** otomatis kalau ada node mati (self-healing).
- **Menemukan node** secara otomatis lewat UDP broadcast.
- **Memvisualisasikan** peta node di terminal.

Semua ini jalan tanpa server pusat. Tidak ada satu titik kegagalan.

---

## Fitur

| # | Fitur | Status |
|---|-------|--------|
| 1 | Sharding (file dipecah) | ✅ |
| 2 | Hash verification (deteksi korup) | ✅ |
| 3 | Replikasi 3x | ✅ |
| 4 | Fault tolerance (2 node mati) | ✅ |
| 5 | Self-healing otomatis | ✅ |
| 6 | Enkripsi AES-256-GCM | ✅ |
| 7 | Network layer (TCP/IP socket) | ✅ |
| 8 | Protokol length-prefix | ✅ |
| 9 | UDP broadcast discovery | ✅ |
| 10 | Visualisasi terminal | ✅ |
| 11 | Key derivation dari password (PBKDF2) | ✅ |

---

## Arsitektur
