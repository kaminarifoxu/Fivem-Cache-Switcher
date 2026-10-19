# Cache aktif di SSD, arsip di HDD

Buka **Peralatan → Pilih folder HDD** dan pilih folder pada HDD yang terhubung. Aplikasi membuat folder arsip tersendiri untuk instalasi FiveM tersebut. Tutup FiveM sebelum memindahkan cache.

Cache kota aktif tetap berada di folder data FiveM. Semua profil kota yang tidak aktif dipindahkan ke arsip. Ketika **Aktifkan** ditekan, aplikasi menyimpan cache sebelumnya ke arsip dan mengembalikan cache pilihan ke folder aktif. Ini berjalan saat berganti profil, bukan berdasarkan waktu idle atau deteksi server yang sedang dimainkan.

Pilih HDD pada drive fisik berbeda untuk mengosongkan SSD. Aplikasi tidak mendeteksi jenis perangkat keras SSD/HDD; drive aktif mengikuti lokasi instalasi FiveM. Memilih folder pada volume yang sama hanya memindahkan lokasi, tidak menambah ruang kosong volume tersebut.

## Keamanan dan pemulihan

Pemindahan lintas drive menyalin data, memverifikasi isi dengan SHA-256, lalu menghapus sumber. Drive tujuan membutuhkan ruang untuk seluruh cache yang dipindahkan. Cache besar membutuhkan waktu; progres penyalinan dan verifikasi ditampilkan. Jangan menjalankan FiveM atau mengubah folder cache selama proses berlangsung.

Jika HDD terlepas, ruang habis, atau aplikasi terhenti, sambungkan kembali drive atau kosongkan ruang lalu pilih **Lanjutkan pemindahan** di Peralatan. Catatan transaksi disimpan agar proses dapat diteruskan. Sumber tidak dihapus sebelum salinan terverifikasi. Jika transaksi belum selesai, peluncuran FiveM dari aplikasi diblokir.

Pilih **Semua di drive FiveM** untuk mengembalikan semua profil ke penyimpanan lokal; pastikan ruangnya cukup. Jangan memindahkan atau menghapus folder arsip secara manual. Folder arsip memiliki penanda kepemilikan untuk mencegah pemakaian folder yang salah.

Fitur ini hanya memindahkan profil cache `server-cache-priv` yang dikelola aplikasi. Instalasi FiveM, `game-storage`, dan cache lain tidak ikut dipindahkan. Cache yang dihapus melalui aplikasi tetap berada di folder sampah untuk pemulihan dan masih memakai ruang pada drive tersebut.
