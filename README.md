# optimai-monitor

Monitor banyak VPS OptimAI dari satu VPS monitor, kirim alert status, report 3 jam, laporan harian, ranking, detail node, riwayat aktivitas ke Telegram, dan dashboard web.

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
- Dashboard web dengan sidebar, overview, card VPS, detail, logs, dan tombol restart
- Urutan VPS natural: 1, 2, 3, ..., 10

## Setup cepat

1. Install dependency:
   - `python3`, `python3-pip`, `openssh-client`
2. Install Python package:
   - `pip3 install -r requirements.txt`
3. Siapkan env:
   - `cp .env.example .env`
   - isi `BOT_TOKEN`, `CHAT_ID`, `REPORT_TIMEZONE`, dan `DASHBOARD_TOKEN`
4. Jalankan bot, lalu kelola daftar VPS lewat menu Telegram.
5. Pastikan SSH key dari VPS monitor sudah bisa login ke semua node tanpa password.
6. Jalankan:
   - `python3 main.py`
   - atau `bash scripts/install.sh` lalu pilih opsi `3`

## Menjalankan bot Telegram dengan systemd

```bash
sudo bash scripts/setup_systemd.sh
sudo systemctl status optimai-monitor
sudo journalctl -u optimai-monitor -f
```

## Menjalankan dashboard web

Install dependency terbaru:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Jalankan test manual dulu:

```bash
python -m uvicorn dashboard:app --host 0.0.0.0 --port 8080
```

Atau install sebagai service:

```bash
sudo bash scripts/setup_dashboard_systemd.sh
sudo systemctl status optimai-dashboard
sudo journalctl -u optimai-dashboard -f
```

Buka dashboard:

```text
http://IP-VPS-MONITOR:8080
```

Tombol restart memakai `DASHBOARD_TOKEN` dari `.env`. Masukkan token itu di kotak `Dashboard token` pada kanan atas dashboard.

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

## Menu Dashboard

- `🏠 Overview`: ringkasan akun dan card semua VPS
- `🖥 VPS Nodes`: card detail semua node
- `🏆 Ranking`: urutan performa harian
- `📅 Daily Report`: riwayat harian
- `📈 Weekly Report`: ringkasan tujuh hari

## Catatan data

- Task dihitung dari assignment ID unik yang ditemukan di journal OptimAI.
- Gagal final berarti assignment memiliki event gagal dan belum pernah sukses submit.
- Retry sukses berarti assignment sempat gagal tetapi akhirnya sukses submit.
- Riwayat disimpan di `data/history.json`.
- Saldo berasal dari satu node sumber karena semua node menggunakan akun OptimAI yang sama.

## Keamanan

Password SSH yang dikirim lewat Telegram hanya digunakan untuk setup SSH key. Tetap disarankan menggunakan login SSH berbasis key.

Dashboard punya tombol restart node. Jangan buka port dashboard ke publik tanpa firewall, tunnel aman, atau token kuat.
