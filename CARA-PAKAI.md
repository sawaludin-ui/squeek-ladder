# Squeek Ladder — cara pakai (30 detik)

Wallet: `0x8346Ac89e4B3297F014050dFe8baf87bF7567e63`
Site live: https://squeek.onerub.net
Vercel: project `squeek-ladder` (scope `fertalites-projects`), domain `onerub.net` dikelola Vercel DNS.

## 1. Masukkan private key (sekali)

Buka file:

```
D:\NXR\squeek\.env
```

Isi baris `PRIVATE_KEY=` jadi:

```
PRIVATE_KEY=0x<64 hex private key wallet kamu>
```

Simpan. File ini lokal, tidak dipakai siapa pun selain script di `tools\`.

## 2. Jalankan (di PowerShell)

```
cd D:\NXR\squeek
python tools\squeek.py check
python tools\squeek.py tester
```

- `check` — baca wallet, gas, jumlah Squeek, gate merge, status checkpoint. Tidak mengirim tx.
- `tester` — kirim **satu transaksi resmi** ke kontrak Squeekchain (`SqueekMining.checkpoint()` bila round sudah settle, kalau belum: `SQK.transfer(self, 0)`). Ini yang memicu badge `code.the_tester`.

Perintah lain:

```
python tools\squeek.py squeeks     # daftar Squeek + level + cooldown
python tools\squeek.py ladder      # rencana merge L1..L10
python tools\squeek.py merge       # jalankan merge yang sudah siap (butuh Squeek)
```

## 3. Yang belum bisa diotomatiskan (butuh login X kamu)

- Link wallet ↔ X di https://squeekchain.com/genesis (tombol LINK X lalu CONNECT WALLET). Signature wallet dibuat oleh dompet yang kamu hubungkan — aku tidak bisa menandatangani lewat situs tanpa ekstensi.
- Submit project di https://squeekchain.com/genesis/code → isi URL `https://squeek.onerub.net`. Sistem akan memberi satu **DNS TXT record**. Kirim record itu ke aku, atau tambahkan sendiri:

```
cd D:\NXR\squeek\site
vercel dns add onerub.net <name-dari-form> TXT "<value-dari-form>"
```

Setelah TXT terpasang, klik verify di halaman project. Badge `code.project_submitted` + `code.early_buildooooor` (slot 88, terpakai 16) langsung masuk.

## Status terverifikasi (5 Nov 2026, WIB)

- Site 200 OK, 26.221 byte, alamat wallet sudah terisi otomatis.
- `check` → 0.846 ETH, 0 Squeek, merges open, max level 10, core block 366, checkpoint round 272 belum settle.
- Tx tester disimulasikan lewat `eth_estimateGas` → 21.125 gas, tidak revert.
