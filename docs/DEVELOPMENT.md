# Panduan kode

- `cache_switcher.py`: titik masuk aplikasi.
- `ganov/core.py`: profil cache, penyimpanan konfigurasi, pemeriksaan versi, dan utilitas Windows.
- `ganov/storage.py`: arsip lintas drive, verifikasi SHA-256, dan pemulihan transaksi.
- `ganov/ui.py`: tampilan desktop, navigasi, dan interaksi tombol.
- `ganov/auto_updater.py`: unduhan dan penggantian EXE.
- `ganov/server_catalog.py` / `server_status.py`: daftar server dan jumlah pemain.
- `ganov/i18n.py` / `app_theme.py`: bahasa dan tema.
- `tests/`: tes otomatis.
- `scripts/`: build dan pemeriksaan UI; `legacy/` hanya arsip alat lama.
- `assets/`: gambar dan ikon; `servers.json`: daftar server yang disinkronkan aplikasi.

Jalankan perintah berikut dari folder utama repositori:

```sh
python -m pip install -r requirements.txt
python cache_switcher.py
python -m unittest discover -v
```

Build dan pemeriksaan UI di Windows:

```sh
python -m scripts.smoke_ui
python -m scripts.smoke_storage_ui
python -m scripts.build_windows
python -m scripts.smoke_packaged_ui
python -m scripts.smoke_frozen_update
```

Workflow GitHub menjalankan tes, pemeriksaan UI, build EXE, pemeriksaan paket dan updater, lalu menerbitkan versi dengan catatan rilis yang sesuai.
