# Squeek Ladder — panduan versi read-only

Situs: https://squeek.onerub.net/
Dashboard Genesis: https://squeek.onerub.net/genesis.html
Sumber: https://github.com/sawaludin-ui/squeek-ladder

## Pakai tanpa private key

1. Buka planner, masukkan alamat publik, lalu muat inventory.
2. Bedakan pasangan yang memenuhi syarat sekarang dari proyeksi yang masih bergantung pada merge sebelumnya.
3. Jika inventory, kepemilikan, chain atau cooldown tidak lengkap, rencana dibatalkan; data kosong tidak dianggap keberhasilan.
4. Dashboard Genesis membaca profil publik, kriteria badge dan leaderboard; tombol ekspor mengunduh snapshot JSON sebagai bukti.

Transaksi dinonaktifkan. Tidak perlu mengisi private key. Perintah lama `tester` dan `merge` tidak boleh dianggap fitur transaksi yang sudah diverifikasi.

## Status proyek dan hadiah

Domain sudah terverifikasi; halaman resmi menunjukkan **IN REVIEW** pada 6 November 2026. Ini bukan persetujuan tim atau penerbitan badge. Pengaitan X/wallet sudah ada, jadi tidak perlu diulang.

Klaim panduan lama bahwa badge langsung masuk setelah TXT dipasang adalah salah. Pemberian badge proyek memerlukan peninjauan tim. Saldo testnet, deployment dan jumlah transaksi bukan bukti Aura bertambah.

## Pemeriksaan lokal

Workspace: `D:\PLER\squeek` (alias `D:\NXR\squeek`). Perintah pengujian dan batas dukungan tercantum di `README.md`. Pengujian inventory berisi token memakai fixture; pengujian wallet live kosong tidak membuktikan seluruh skenario berisi token. Planner ini hanya mendukung custody wallet, bukan token yang sedang disetor/staking.
