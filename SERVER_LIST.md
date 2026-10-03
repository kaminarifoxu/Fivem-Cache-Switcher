# Mengubah daftar server

Edit [servers.json](servers.json) di branch `main`, lalu commit. Pengguna v2.5.0 dan berikutnya menerima perubahan saat aplikasi dibuka, setiap 5 menit, atau lewat **Daftar server → Sync server**. Tidak perlu mengganti VERSION atau menerbitkan EXE baru.

Contoh satu entri dalam array `servers`:

```json
{
  "id": "nama-kota",
  "name": "Nama Kota Roleplay",
  "join_code": "abc123",
  "description": {
    "id": "Deskripsi server dalam bahasa Indonesia.",
    "en": "Server description in English."
  },
  "source_url": "https://cfx.re/join/abc123"
}
```

Ganti `abc123` dengan kode join server yang sebenarnya. `id` harus unik. `join_code` hanya berisi 6–10 huruf kecil/angka, tanpa URL atau perintah. Jangan ubah `schema_version: 1`. Untuk menghapus server, hapus entrinya dari array.

Daftar awal diperiksa pada 3 Oktober 2026 menggunakan halaman join Cfx.re. Ini pilihan komunitas Indonesia dengan jejak jumlah pemain besar, bukan peringkat pemain langsung. Kode join dapat berubah; whitelist, antrean, dan persyaratan bergabung ditentukan masing-masing server. Connect membuka handler FiveM yang terdaftar di Windows; jalankan FiveM sekali bila handler belum terdaftar. Daftar tidak mengubah cache atau profil secara otomatis.

Saat offline atau JSON tidak valid, aplikasi mempertahankan daftar valid terakhir. Nama/deskripsi merupakan data dan tidak dijalankan sebagai kode.

Jumlah pemain / kapasitas dan deskripsi diambil dari API daftar server FiveM (`frontend.cfx-services.net`). Angka merupakan snapshot dan dapat tertunda. Aplikasi memeriksa setiap menit saat halaman server dibuka; kegagalan tidak dianggap nol pemain. Open page menggunakan kode join yang sama untuk halaman detail di servers.fivem.net.
