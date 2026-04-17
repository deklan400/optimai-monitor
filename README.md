# optimai-monitor

Monitor banyak VPS Optimai dari 1 VPS monitor (Ubuntu 22), kirim alert status realtime (berdasarkan interval check) dan report reward tiap 3 jam ke Telegram.
Manajemen VPS dilakukan lewat tombol menu Telegram (tanpa perlu command teks).

## Setup cepat

1. Install dependency:
   - `python3`, `python3-pip`, `openssh-client`
2. Install Python package:
   - `pip3 install -r requirements.txt`
3. Siapkan env:
   - `cp .env.example .env`
   - isi `BOT_TOKEN` dan `CHAT_ID`
4. Jalankan bot, lalu kelola daftar VPS lewat menu Telegram:
   - `📋 List VPS`
   - `➕ Tambah VPS`
   - `❌ Hapus VPS`
   - `⚡ Check Manual` untuk cek langsung tanpa tunggu report 3 jam
   - saat tambah VPS, bot bisa minta password SSH untuk auto setup `ssh-copy-id`
5. Pastikan SSH key dari VPS monitor sudah bisa login ke semua node tanpa password.
6. Jalankan bot:
   - `python3 main.py`
   - atau setup service otomatis: `bash scripts/install.sh` lalu pilih opsi `3`

## Menjalankan dengan systemd (disarankan)

1. Pastikan dependency + `.env` sudah siap (paling gampang via `bash scripts/install.sh`)
2. Install service:
   - `sudo bash scripts/setup_systemd.sh`
3. Cek status:
   - `sudo systemctl status optimai-monitor`
4. Cek log real-time:
   - `sudo journalctl -u optimai-monitor -f`
5. Restart manual jika perlu:
   - `sudo systemctl restart optimai-monitor`

## Output bot

- Alert saat node down: `⚠️ vpsX : ❌ DOWN`
- Alert saat node hidup lagi: `✅ vpsX : RUNNING KEMBALI`
- Report 3 jam:
  - `🔥 OPTIMAI REPORT (3 JAM)`
  - per node: `vpsX : ✅|❌ | +N`
  - total: `💰 Total 3 Jam` dan `💰 Total All`

## Catatan keamanan

- Password SSH yang dikirim lewat Telegram dipakai sekali untuk setup key, lalu dibuang.
- Tetap disarankan setelah setup selesai gunakan login SSH berbasis key, bukan password.
