# Copyright (c) 2026 GANOMABI / amiinarii.
import json
from pathlib import Path

LANGUAGE = "id"
EN = {
    "Hanya cache kota nonaktif yang dipindahkan. Cache aktif tetap di drive FiveM.": "Only inactive city caches will move. Active cache stays on the FiveM drive.",
    "CACHE NONAKTIF": "INACTIVE CACHES",
    "DRIVE FIVEM": "FIVEM DRIVE",
    "LOKASI TUJUAN": "DESTINATION FOLDER",
    "Pindahkan cache": "Move caches",
    "Kembalikan cache": "Return caches",
    "Tutup FiveM dan biarkan kedua drive tersambung selama transfer.": "Keep FiveM closed and both drives connected during the transfer.",
    "Tutup FiveM sebelum mengganti cache.": "Close FiveM before switching cache.",
    "Tambah kota": "Add city",
    "Daftar kota": "Cities",
    "Instalasi": "Installation",
    "Belum ada profil": "No profiles yet",
    "Profil kota": "City profiles",
    "Peralatan": "Tools",
    "Jalankan FiveM": "Launch FiveM",
    "Pilih FiveM.exe": "Select FiveM.exe",
    "Cek update": "Check for updates",
    "Donasi": "Donate",
    "+ Tambah kota": "+ Add city",
    "Aktifkan": "Activate",
    "Nama": "Rename",
    "Hapus": "Delete",
    "Batal": "Cancel",
    "Bersihkan": "Clean",
    "Mengerti": "Got it",
    "Tutup": "Close",
    "Nanti": "Later",
    "Terkini": "Up to date",
    "Coba lagi": "Retry",
    "Sedang aktif": "Active",
    "PROFIL KOTA": "CITY PROFILES",
    "PROFIL KOTA  /  ": "CITY PROFILES  /  ",
    " PROFIL": " PROFILES",
    "0 PROFIL": "0 PROFILES",
    "CACHE AKTIF": "ACTIVE CACHE",
    "AKTIF  /  ": "ACTIVE  /  ",
    "TERSIMPAN  /  ": "SAVED  /  ",
    " tersimpan": " saved",
    "0 B tersimpan": "0 B saved",
    "Menghitung...": "Calculating...",
    "Belum diketahui": "Unknown",
    "Belum ada cache aktif": "No active cache",
    "Cache lama belum terdaftar": "Unregistered previous cache",
    "Backup perlu diperiksa": "Backup needs inspection",
    "Backup tidak ditemukan": "Backup not found",
    "Switch perlu dipulihkan": "Switch recovery required",
    "Instalasi terhubung": "Installation connected",
    "Pilih FiveM.exe untuk mulai": "Select FiveM.exe to begin",
    "FiveM.exe belum dipilih": "FiveM.exe not selected",
    "CACHE  /  menunggu lokasi FiveM.exe": "CACHE  /  waiting for FiveM.exe",
    "SATU KOMUNITAS. BANYAK KOTA.": "ONE COMMUNITY. MANY CITIES.",
    "Tutup FiveM sebelum switch. Cache kota disimpan secara terpisah.": "Close FiveM before switching. Each city cache is stored separately.",
    "Perjalanan baru dimulai di sini.": "Your journey starts here.",
    "Pilih FiveM.exe, lalu tambahkan kota pertamamu.": "Select FiveM.exe, then add your first city.",
    "Siap. Pilih FiveM.exe untuk menghubungkan instalasimu.": "Ready. Select FiveM.exe to link your installation.",
    "Siap. Pilih kota yang ingin kamu aktifkan.": "Ready. Select the city you want to activate.",
    "PERALATAN": "TOOLS",
    "Kontrol instalasi, file sementara, dan jaringanmu.": "Manage your installation, temporary files, and network.",
    "INSTALASI & PEMULIHAN": "INSTALLATION & RECOVERY",
    "Buka lokasi cache atau pulihkan switch yang belum selesai.": "Open your cache folder or recover an interrupted switch.",
    "Buka folder data": "Open data folder",
    "Pulihkan Switch": "Recover switch",
    "Bersihkan file sementara. File terkunci akan dilewati.": "Clean temporary files. Locked files will be skipped.",
    "Pilih adapter. Pengaturan DNS memerlukan administrator.": "Select an adapter. DNS changes require administrator privileges.",
    "Pilih adapter": "Select adapter",
    "Semua Temp": "All Temp",
    "Terapkan DNS": "Apply DNS",
    "Menyiapkan aplikasi...": "Preparing application...",
    "Membaca konfigurasi dan lokasi FiveM...": "Reading settings and FiveM location...",
    "Menyiapkan profil kota dan tampilan...": "Preparing city profiles and interface...",
    "Siap. Selamat datang di GANOMABI.": "Ready. Welcome to GANOMABI.",
    "Aplikasi gagal dibuka": "Application startup failed",
    "Aplikasi sudah terbuka.": "The application is already open.",
    "Konfigurasi": "Settings",
    "Buka tautan": "Open link",
    "Browser tidak dapat dibuka.\n": "Unable to open browser.\n",
    "Mengunduh update: ": "Downloading update: ",
    "Mengunduh update... ": "Downloading update... ",
    "Tidak dapat mengecek update.": "Unable to check for updates.",
    "Update tersedia: v": "Update available: v",
    "Belum ada versi yang lebih baru.": "No newer version is available.",
    "Operasi gagal": "Operation failed",
    "Operasi gagal. Lihat pesan untuk detail.": "Operation failed. See the message for details.",
    "Mengecek update...": "Checking for updates...",
    "Pembaruan | ": "Updates | ",
    "GANOMABI  /  PEMBARUAN": "GANOMABI  /  UPDATES",
    "Update tersedia": "Update available",
    "Cek update gagal": "Update check failed",
    "Versi kamu sudah terbaru": "Your version is up to date",
    "Unduh dan pasang langsung dari aplikasi.": "Download and install directly from the app.",
    "Coba lagi saat koneksi tersedia.": "Try again when your connection is available.",
    "Belum ada rilis stabil yang lebih baru.": "No newer stable release is available.",
    "VERSI TERPASANG": "INSTALLED VERSION",
    "VERSI BARU": "NEW VERSION",
    "Update diunduh langsung, lalu aplikasi akan ditutup dan dibuka kembali. EXE lama diganti di lokasi yang sama. Pengaturan tetap tersimpan.": "The update downloads directly, then the app closes and restarts. The EXE is replaced in the same location. Your settings are preserved.",
    "Update belum dapat diselesaikan. ": "The update could not be completed. ",
    "Kamu bisa melanjutkan menggunakan aplikasi. Kami akan memberi notifikasi ketika rilis baru tersedia di GitHub.": "You can continue using the app. We will notify you when a new release is available on GitHub.",
    "Gunakan EXE Windows untuk memasang update otomatis.": "Use the Windows EXE to install updates automatically.",
    "Mengunduh...": "Downloading...",
    "Menyiapkan unduhan...": "Preparing download...",
    "Update sekarang": "Update now",
    "Update gagal. EXE lama tetap tersedia.": "Update failed. The previous EXE is still available.",
    "Hubungkan FiveM": "Link FiveM",
    "Tambah kota / cache": "Add city / cache",
    "Nama kota atau profil cache": "City or cache profile name",
    "Tambah kota": "Add city",
    "Membuat profil...": "Creating profile...",
    "Profil dibuat.": "Profile created.",
    "Ubah nama profil": "Rename profile",
    "Simpan nama": "Save name",
    "Menyimpan nama...": "Saving name...",
    "Nama diperbarui.": "Name updated.",
    "Contoh: GANOMABI City": "Example: GANOMABI City",
    "Setiap kota memiliki cache yang terpisah.": "Each city has a separate cache.",
    "Isi nama kota terlebih dahulu.": "Enter a city name first.",
    "Hapus profil": "Delete profile",
    "Hapus profil '": "Delete profile '",
    "'?\n\nCache dipindahkan ke cache-switcher-trash dan bisa dipulihkan manual.": "'?\n\nThe cache is moved to cache-switcher-trash and can be restored manually.",
    "Memindahkan cache...": "Moving cache...",
    "Mengaktifkan ": "Activating ",
    "Cache aktif: ": "Active cache: ",
    "Cache disimpan di: ": "Cache saved at: ",
    "Pilih lokasi data": "Select data location",
    "Ada beberapa lokasi data atau folder data belum terdeteksi.\nPilih folder data yang berisi server-cache-priv milik FiveM ini.": "Multiple data folders were found, or no data folder was detected.\nSelect the data folder containing server-cache-priv for this FiveM installation.",
    "Pilih folder data milik FiveM ini": "Select this FiveM installation's data folder",
    "Ganti instalasi": "Change installation",
    "Tampilkan profil milik instalasi yang baru?\nCache instalasi sebelumnya tetap tersedia di folder asal.": "Show profiles for the new installation?\nThe previous installation's cache remains in its original folder.",
    "Menghubungkan FiveM.exe...": "Linking FiveM.exe...",
    "FiveM terhubung. Backup kota yang ditemukan ditampilkan.": "FiveM linked. Existing city backups are displayed.",
    "Lokasi FiveM": "FiveM location",
    "Launch gagal": "Launch failed",
    "Pemulihan": "Recovery",
    "Tidak ada switch yang perlu dipulihkan.": "No switch recovery is needed.",
    "Memulihkan switch...": "Recovering switch...",
    "Cache sebelumnya dipulihkan.": "Previous cache restored.",
    "Bersihkan Temp": "Clean Temp",
    "Hapus isi folder berikut?\n\n": "Delete the contents of these folders?\n\n",
    "\n\nFile yang dipakai atau terkunci akan dilewati.": "\n\nFiles in use or locked will be skipped.",
    " item dibersihkan, ": " items removed, ",
    " dilewati.": " skipped.",
    "Membersihkan Temp...": "Cleaning Temp...",
    "Adapter": "Adapter",
    "Tidak ada adapter aktif yang terdeteksi.": "No active adapter was detected.",
    "Ubah DNS": "Change DNS",
    "Terapkan ": "Apply ",
    " pada adapter '": " to adapter '",
    "Mengatur DNS...": "Applying DNS...",
    " diterapkan ke ": " applied to ",
    "Sedang bekerja": "Working",
    "Tunggu operasi selesai sebelum menutup aplikasi.": "Wait for the current operation to finish before closing the app.",
    "Daftar server": "Server list",
    "SERVER INDONESIA": "INDONESIAN SERVERS",
    "Sync server": "Sync servers",
    "Sinkronisasi dari GitHub...": "Syncing from GitHub...",
    "Daftar tersinkron dari GitHub.": "Server list synced from GitHub.",
    "Sync gagal; daftar terakhir tetap tersedia.": "Sync failed; the last saved list is still available.",
    "Tidak ada server dalam daftar.": "No servers in the catalog.",
    "Hubungkan": "Connect",
    "Buka halaman": "Open page",
    "Daftar diperbarui otomatis dari GitHub. Syarat whitelist dan antrean mengikuti aturan server.": "The list updates automatically from GitHub. Whitelists and queues follow each server's rules.",
    "Menghubungkan ke ": "Connecting to ",
    "Koneksi server": "Server connection",
    "FiveM belum terdaftar sebagai pembuka tautan. Jalankan FiveM sekali, lalu coba lagi.": "FiveM is not registered to open links. Launch FiveM once, then try again.",
}


def tr(text):
    return EN.get(text, text) if LANGUAGE == "en" else text


def load(path):
    global LANGUAGE
    try:
        value = json.loads(Path(path).read_text()).get("language")
        LANGUAGE = value if value in ("id", "en") else "id"
    except (OSError, ValueError):
        LANGUAGE = "id"


def set_language(language, path):
    global LANGUAGE
    if language not in ("id", "en"):
        raise ValueError("Invalid language")
    target = Path(path)
    temporary = target.with_suffix(".new")
    temporary.write_text(json.dumps({"language": language}), encoding="utf-8")
    temporary.replace(target)
    LANGUAGE = language


EN.update(
    {
        "BAHASA APLIKASI": "APP LANGUAGE",
        "pemain": "players",
        "Jumlah pemain belum tersedia": "Player count unavailable",
    }
)

EN.update(
    {
        "List server": "Server list",
        "Pilih server dan hubungkan melalui FiveM.": "Choose a server and connect through FiveM.",
        "Belum tersedia": "Unavailable",
    }
)

EN.update({"Sebelumnya": "Previous", "Berikutnya": "Next", "Halaman": "Page"})

EN.update(
    {
        "Yang baru": "What’s new",
        "Ringkasan belum tersedia. Lihat catatan rilis di GitHub.": "No summary is available. See the release notes on GitHub.",
    }
)

EN.update({"TEMA APLIKASI": "APP THEME", "Terang": "Light", "Gelap": "Dark"})

EN.update({"Membuka panel update...": "Opening update panel..."})

EN.update(
    {
        "Pengaturan aplikasi": "App settings",
        "File sementara": "Temporary files",
        "Jaringan DNS": "DNS network",
    }
)


EN.update(
    {
        "Cache manager": "Cache manager",
        "DRIVE FIVEM / CACHE AKTIF": "FIVEM DRIVE / ACTIVE CACHE",
        "ARSIP CACHE / HDD PILIHAN": "CACHE ARCHIVE / CHOSEN HDD",
        "SIAP DI DRIVE AKTIF": "READY ON THE ACTIVE DRIVE",
        "Penyimpanan": "Storage",
        "Penyimpanan SSD / HDD": "SSD / HDD storage",
        "Pilih folder HDD": "Choose HDD folder",
        "Pilih folder arsip di HDD": "Choose a cache archive folder on your HDD",
        "Semua di drive FiveM": "All on FiveM drive",
        "Lanjutkan transfer": "Resume transfer",
        "Tidak tersedia": "Unavailable",
        "HDD belum dipilih / offline": "HDD not selected / offline",
        "kosong": "free",
        "Semua cache di drive FiveM": "All caches on FiveM drive",
        "Belum ada folder arsip. Pilih folder di HDD untuk menghemat ruang.": "No archive selected. Choose an HDD folder to save space.",
        "Aktif tetap di drive FiveM. Nonaktif dipindahkan ke arsip; verifikasi selesai sebelum sumber dihapus.": "Active cache stays on the FiveM drive. Inactive caches move to the archive; sources are removed only after verification.",
        "Pindahkan cache nonaktif?": "Move inactive caches?",
        "Cache kota nonaktif akan dipindahkan ke folder arsip ini. Cache aktif tetap di drive FiveM. Proses dapat memakan waktu; jangan cabut drive atau membuka FiveM.": "Inactive city caches will move to this archive. Active cache stays on the FiveM drive. Transfers may take time; keep both drives connected and FiveM closed.",
        "Menyiapkan arsip HDD...": "Preparing HDD archive...",
        "Arsip HDD siap. Cache nonaktif sudah dipindahkan.": "HDD archive ready. Inactive caches have been moved.",
        "Kembalikan cache ke drive FiveM?": "Return caches to the FiveM drive?",
        "Semua cache nonaktif akan disalin kembali. Pastikan ruang drive FiveM cukup.": "All inactive caches will be copied back. Make sure the FiveM drive has enough free space.",
        "Mengembalikan cache...": "Returning caches...",
        "Semua cache tersimpan di drive FiveM.": "All caches are stored on the FiveM drive.",
        "Memeriksa sumber": "Checking source",
        "Menyalin cache": "Copying cache",
        "Verifikasi SHA-256": "SHA-256 verification",
        "Menyelesaikan transfer": "Finalizing transfer",
        "Transfer tertunda. Sambungkan drive, sediakan ruang, lalu pilih Lanjutkan transfer di Peralatan.": "Transfer paused. Connect the drive, free space, then choose Resume transfer in Tools.",
        "Tutup FiveM sebelum transfer. Arsip akan kembali ke drive FiveM saat diaktifkan.": "Close FiveM before transferring. Archived caches return to the FiveM drive when activated.",
        "DRIVE AKTIF": "ACTIVE DRIVE",
        "LOKAL": "LOCAL",
        "ARSIP HDD": "HDD ARCHIVE",
        "HDD OFFLINE": "HDD OFFLINE",
        "BELUM ADA": "MISSING",
        "Transfer / pemulihan selesai.": "Transfer / recovery completed.",
        "Transfer belum selesai": "Transfer incomplete",
        "Selesaikan transfer sebelum menjalankan FiveM.": "Complete the transfer before launching FiveM.",
    }
)

