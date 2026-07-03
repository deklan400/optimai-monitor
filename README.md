# optimai-monitor

Monitor banyak VPS OptimAI dari satu VPS monitor, kirim alert status, report 3 jam, laporan harian, ranking, detail node, dan riwayat aktivitas ke Telegram.

## Fitur

- Status semua node dan alert DOWN/RUNNING KEMBALI
- Check Manual dengan data kumulatif sejak pukul 00:00
- Assignment dihitung berdasarkan ID unik
- Submit sukses, gagal final, pending, dan retry sukses
- Report otomatis setiap 3 jam
- Report harian setelah pergantian hari
- Ranking performa harian
- Detail satu VPS: status, RAM, disk, Docker, uptime, dan aktivitas
- Riwayat harian dan ringkasan 7 hari
- Urutan VPS natural: 1, 2, 3, ..., 10

## Setup cepat

1. Install dependency:
   - `python3`, `python3-pip`, `openssh-client`
2. Install Python package:
   - `pip3 install -r requirements.txt`
3. Siapkan env:
   - `cp .env.example .env`
   - isi `BOT_TOKEN`, `CHAT_ID`, dan `REPORT_TIMEZONE`
4. Jalankan bot, lalu kelola daftar VPS lewat menu Telegram.
5. Pastikan SSH key dari VPS monitor sudah bisa login ke semua node tanpa password.
6. Jalankan:
   - `python3 main.py`
   - atau `bash scripts/install.sh` lalu pilih opsi `3`

## Menjalankan dengan systemd

```bash
sudo bash scripts/setup_systemd.sh
sudo systemctl status optimai-monitor
sudo journalctl -u optimai-monitor -f
```

## Menu Telegram

- `📋 List VPS`
- `➕ Tambah VPS`
- `✏️ Edit VPS`
- `❌ Hapus VPS`
- `🔍 Test SSH`
- `⚡ Check Manual`
- `🔎 Detail VPS`
- `🏆 Ranking Harian`
- `📅 Riwayat Harian`
- `📈 Riwayat Mingguan`

## Catatan data

- Task dihitung dari assignment ID unik yang ditemukan di journal OptimAI.
- Gagal final berarti assignment memiliki event gagal dan belum pernah sukses submit.
- Retry sukses berarti assignment sempat gagal tetapi akhirnya sukses submit.
- Riwayat disimpan di `data/history.json`.
- Saldo berasal dari satu node sumber karena semua node menggunakan akun OptimAI yang sama.

## Keamanan

Password SSH yang dikirim lewat Telegram hanya digunakan untuk setup SSH key. Tetap disarankan menggunakan login SSH berbasis key.
