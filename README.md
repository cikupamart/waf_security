# WAF Security untuk Odoo 18 

Modul ini Web Application
Firewall (WAF) yang terintegrasi langsung di dalam aplikasi Odoo.

## Catatan Porting (Odoo 16 -> 17 -> 18)

Modul ini adalah hasil porting bertahap dari versi Odoo 16. Perubahan
teknis yang dilakukan sepanjang porting ke Odoo 18:

1. **Syntax `attrs`/`states` dihapus** (sejak Odoo 17) — 
   `attrs="{'invisible': [...]}"` diganti ke syntax langsung, mis.
   `invisible="not enable_rate_limiting"`.
2. **Signature `res.users._login()` berubah** (sejak Odoo 17) — dari
   `(db, login, password, user_agent_env)` di Odoo 16, menjadi
   `(db, credential, user_agent_env)` di mana `credential` adalah dict
   (bagian dari refactor autentikasi untuk mendukung API key, passkey,
   dll sebagai jenis credential berbeda). Override brute force protection
   di `models/res_users.py` sudah disesuaikan, dan sepengetahuan kami
   masih berlaku sama persis di Odoo 18.0.
3. **Tag view `<tree>` diganti `<list>`** (sejak Odoo 18) — root tag
   arch untuk list view, serta token `tree` di `view_mode` pada
   `ir.actions.act_window`, semuanya diganti ke `list`. Odoo 18 disebut
   masih mempertahankan `<tree>` sebagai alias untuk kompatibilitas
   mundur, tapi modul ini sudah memakai `<list>` langsung sebagai standar
   yang direkomendasikan ke depannya.

**PENTING:** karena poin ke-2 menyentuh mekanisme login inti, WAJIB diuji
manual di staging dulu sebelum dipakai di production, di versi Odoo 18
persis yang Anda pakai (bukan diasumsikan dari dokumentasi):
- Login normal via `/web/login` (harus tetap berhasil)
- Login gagal berkali-kali (harus ter-log di Audit Log dan IP ter-ban
  sesuai threshold yang dikonfigurasi)
- Login via API key/XML-RPC/JSON-RPC eksternal (jenis credential lain)
  harus tetap berfungsi normal, tidak ikut ke-block oleh logika brute
  force yang didesain untuk login form
- Buka menu Dashboard, Audit Log, IP Rule (yang sekarang pakai `<list>`)
  dan pastikan tampil normal

Sisanya (deteksi ancaman, rate limiting, IP rule, security headers,
subscription monitor) tidak menyentuh API inti Odoo yang berubah antar
versi, jadi logikanya sama persis dengan versi-versi sebelumnya.

## Cara Instalasi

1. Salin folder `waf_security` ke dalam addons path Odoo 18, misalnya:
   ```
   /opt/odoo18/custom-addons/waf_security
   ```
2. Restart service Odoo dan update apps list:
   ```
   ./odoo-bin -c odoo.conf -u base --stop-after-init
   ```
   atau melalui UI: Apps > Update Apps List.
3. Cari "WAF Security" di menu Apps, lalu klik **Install**.
4. Setelah terinstall, menu **WAF Security** akan muncul di sidebar utama
   (hanya terlihat oleh user yang tergabung dalam group `WAF: Viewer` atau
   `WAF: Administrator`). Secara default, Administrator Odoo otomatis
   masuk ke group Administrator WAF.

## Struktur Menu

* **Dashboard** — ringkasan grafik & statistik ancaman yang terdeteksi.
* **Audit Log** — daftar lengkap semua kejadian yang dicatat WAF.
* **IP Whitelist/Blacklist** — kelola IP yang selalu diizinkan/diblokir.
* **Konfigurasi** — atur seluruh perilaku WAF (deteksi, rate limit,
  brute force, security headers, alert email/telegram).

## Konsep yang Dipelajari

1. **Request Inspection** — dilakukan dengan meng-override method
   `_dispatch()` pada model `ir.http`, yang merupakan titik masuk semua
   HTTP request di Odoo (`models/ir_http.py`).
2. **Signature-based Detection** — pola regex untuk SQLi, XSS, RCE, dan
   Path Traversal ada di `models/waf_detection_engine.py`. Silakan
   modifikasi/tambahkan pattern untuk latihan.
3. **Rate Limiting & Brute Force** — menggunakan sliding window counter
   in-memory (`models/waf_rate_limiter.py`). Proteksi brute force login
   di-hook lewat override `res.users._login()`.
4. **Auto Ban** — ketika jumlah pelanggaran suatu IP melewati ambang
   batas dalam periode waktu tertentu, IP otomatis dimasukkan ke
   blacklist dengan masa berlaku (expire) tertentu.
5. **Security Headers** — CSP, HSTS, X-Frame-Options, X-Content-Type-Options,
   dll ditambahkan ke setiap response.
6. **Audit Log & Alerting** — setiap kejadian dicatat ke model `waf.log`,
   dan bila severity-nya melewati ambang, dikirim alert lewat email
   (`mail.mail`) dan/atau Telegram Bot API.

## Batasan (Penting untuk Dipahami)

* Rate limiting & brute force tracker bersifat **in-memory per worker
  process**. Jika Odoo dijalankan multi-worker, counter tidak dibagi
  antar worker. Untuk production sungguhan, gunakan penyimpanan
  terpusat seperti Redis.
* Deteksi berbasis regex/signature bisa di-*bypass* dengan teknik
  encoding/obfuscation tingkat lanjut — ini contoh keterbatasan nyata
  dari pendekatan signature-based, cocok jadi bahan diskusi kelas.
* Modul ini **bukan pengganti** WAF layer jaringan/proxy production
  (Cloudflare, AWS WAF, Nginx+ModSecurity). Gunakan sebagai lapisan
  tambahan (defense in depth) dan sebagai media belajar.
* Uji coba pattern SQLi/XSS/dsb sebaiknya dilakukan di environment
  development/lab milik sendiri, bukan sistem produksi orang lain.

## Fitur Tambahan (Opsional, OFF Secara Default)


Log setiap percobaan sync (berhasil/gagal, payload yang terkirim, response
server) tetap terlihat di menu **WAF Security > Subscription Monitor Log**
(khusus group Administrator WAF) — ini sengaja tidak disembunyikan, supaya
siapa pun yang mengelola instance selalu bisa melihat data apa saja yang
sudah/akan terkirim ke luar.


## Contoh Skenario Latihan untuk Murid

1. Coba akses `/web?x=<script>alert(1)</script>` pada instance dev lokal,
   lihat apakah tercatat di Audit Log sebagai `xss`.
2. Ubah `block_mode` ke `monitor`, ulangi request yang sama, amati bedanya
   (tidak diblokir, hanya dicatat).
3. Coba login gagal berkali-kali dan amati kapan IP otomatis di-ban.
4. Tambahkan pattern regex baru di `waf_detection_engine.py` lalu uji.

