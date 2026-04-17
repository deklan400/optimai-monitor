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
5. Pastikan SSH key dari VPS monitor sudah bisa login ke semua node tanpa password.
6. Jalankan bot:
   - `python3 main.py`

## Output bot

- Alert saat node down: `⚠️ vpsX : ❌ DOWN`
- Alert saat node hidup lagi: `✅ vpsX : RUNNING KEMBALI`
- Report 3 jam:
  - `🔥 OPTIMAI REPORT (3 JAM)`
  - per node: `vpsX : ✅|❌ | +N`
  - total: `💰 Total 3 Jam` dan `💰 Total All`
