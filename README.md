# GanoV-Cache-Switch v2.3.0

**Copyright (c) 2026 GANOMABI / amiinarii.**

Lihat COPYRIGHT.md untuk atribusi proyek dan komponen pihak ketiga.

Windows 10/11 64-bit. Tema hitam, merah, dan emas dengan logo GANOMABI dan maskot rubah. Loading screen tampil saat inisialisasi, dan dialog tambah kota/ubah nama mengikuti tema aplikasi.

## Cara memakai

1. Unduh [GanoV-Cache-Switch.exe](https://github.com/kaminarifoxu/Fivem-Cache-Switcher/raw/refs/heads/main/GanoV-Cache-Switch.exe) dan simpan di folder yang dapat ditulis.
2. Jalankan **GanoV-Cache-Switch.exe**.
3. Klik **Pilih FiveM.exe** dan pilih launcher instalasi FiveM kamu.
4. Aplikasi mendeteksi folder data dan menampilkan backup kota yang sudah ada.
5. Tutup FiveM, pilih profil, lalu klik **Aktifkan**.
6. Klik **Jalankan FiveM** untuk membuka launcher yang dipilih.

EXE dapat dijalankan sendiri. Python dan file PNG terpisah tidak diperlukan; semua gambar dan ikon UI dibundel dalam EXE. File remake_config.json dibuat untuk menyimpan pengaturan.

## Notifikasi update

Saat dibuka, aplikasi mengecek rilis stabil terbaru dari GitHub di latar belakang. Jika ada versi lebih baru, muncul dialog **Update tersedia** dengan tombol **Unduh update** dan **Nanti**. Tombol **Cek update** di sidebar dapat dipakai kapan saja. Jika internet tidak tersedia, aplikasi tetap berfungsi.

**Unduh update** membuka halaman rilis di browser. Unduh EXE, tutup aplikasi, lalu ganti EXE lama. Simpan remake_config.json di folder EXE untuk mempertahankan profil. Pembaruan tidak mengganti EXE secara otomatis.

### Menerbitkan pembaruan berikutnya

1. Ubah VERSION di cache_switcher.py, misalnya menjadi 2.4.0.
2. Commit dan push perubahan ke GitHub.
3. Buat tag yang sama, lalu push:

       git tag v2.4.0
       git push origin v2.4.0

GitHub Actions menjalankan tes, membangun EXE Windows dengan logo/copyright GANOMABI, lalu menerbitkan GitHub Release beserta EXE. Tag harus sama dengan VERSION. Commit source saja belum memicu notifikasi; rilis baru harus sudah terbit. Instal EXE v2.3.0 ini terlebih dahulu untuk menerima notifikasi berikutnya.

## Deteksi lokasi

Pemilihan dimulai dari file **FiveM.exe**. Nama folder aplikasi tidak harus FiveM.app.

Contoh sesuai instalasimu:

    E:\FiveM\FiveM.exe
      -> E:\FiveM\FiveM Application Data\data\server-cache-priv

Lokasi yang didukung:

- Folder data tepat di sebelah FiveM.exe.
- FiveM Application Data\data di sebelah FiveM.exe.
- FiveM.app\data di sebelah FiveM.exe.
- Folder aplikasi lain di satu tingkat di bawah folder launcher, jika terdapat cache FiveM.

Jika ada beberapa lokasi cache atau lokasi belum ditemukan, aplikasi meminta kamu memilih folder data milik instalasi tersebut. Cache aktif memakai server-cache-priv; backup kota memakai server-cache-priv_<ID>.

Backup yang ditemukan muncul dengan nama dari ID folder, misalnya Kota A. Nama dapat diubah lewat tombol **Nama**. Cache aktif tanpa identitas yang tercatat ditampilkan sebagai **Cache lama belum terdaftar**. Saat beralih kota, cache tersebut disimpan menjadi profil **Cache sebelumnya**.

## Memakai konfigurasi lama

Untuk mempertahankan nama dan identitas profil, salin remake_config.json dari versi sebelumnya ke folder EXE baru. Jika belum ada file tersebut, aplikasi juga bisa membaca config.json milik program original.

Konfigurasi menyimpan lokasi FiveM.exe, lokasi data, nama profil, dan profil aktif. Pemilihan ulang FiveM.exe pada instalasi yang sama mempertahankan nama profil. Memilih instalasi lain menampilkan backup instalasi itu; cache instalasi sebelumnya tetap di tempatnya.

## Halaman aplikasi

- **Profil kota**: status aktif, ukuran cache, tambah kota, aktifkan, ubah nama, hapus.
- **Peralatan**: buka folder data, pulihkan switch, Windows Temp Cleaner, pengaturan DNS.

Switch memakai rename folder, memeriksa proses FiveM, dan menyediakan rollback serta pemulihan setelah switch terhenti. Jika ada journal yang belum selesai, gunakan **Peralatan > Pulihkan Switch**.

Profil yang dihapus dipindahkan ke data/cache-switcher-trash. Untuk pemulihan manual, tutup FiveM dan aplikasi, pindahkan folder tersebut kembali menjadi server-cache-priv_<ID> di folder data dan tambahkan ID/nama ke profiles dalam konfigurasi. Jangan menimpa folder yang sudah ada.

Temp Cleaner meminta konfirmasi, melewati file terkunci, symlink/junction, dan folder runtime aplikasi. System Temp bisa memerlukan administrator. DNS mengubah pengaturan IPv4 adapter yang dipilih dan memerlukan **Run as administrator**. Jika konfigurasi DNS gagal di tengah proses, sebagian perubahan mungkin sudah diterapkan; pilih **Default (ISP)** untuk kembali ke DHCP.

## Source dan build

Source dan aset build tersedia di repository ini. Untuk memakai aplikasi, cukup jalankan GanoV-Cache-Switch.exe.

- cache_switcher.py: source aplikasi.
- assets: aset untuk membangun ulang source; tidak diperlukan di samping EXE.
- test_cache_switcher.py: tes operasi cache dan deteksi instalasi.
- build_windows.py: build EXE dengan metadata versi dan copyright.
- .github/workflows/release.yml: build dan publikasi rilis saat tag versi di-push.
- build_windows.bat: build baru di Windows dari source; memerlukan Python.
- build_from_original.py: build alternatif dengan Python 3.14 dan runtime EXE original.

Build alternatif:

    python build_from_original.py "FiveM Cache Switcher.exe"

Tes:

    python -m unittest discover -v

EXE yang disertakan memakai bootloader, Python 3.14, dan dependensi dari EXE original; source aplikasi dan aset GANOMABI dibundel ulang. Ikon file EXE, ikon jendela, nama produk, dan metadata copyright memakai identitas GanoV-Cache-Switch / GANOMABI / amiinarii.

Pemeriksaan core menggunakan direktori sementara di Linux. UI diperiksa melalui virtual display di Linux. Launch FiveM, DNS, Windows Temp, dan EXE belum diuji langsung pada komputer Windows/FiveM.
