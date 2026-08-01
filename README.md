# WAF Security untuk Odoo 16 

Modul ini dibuat untuk tujuan Web Application
Firewall (WAF) yang terintegrasi langsung di dalam aplikasi Odoo.

## Cara Instalasi

1. Salin folder `waf_security` ke dalam addons path Odoo 16, misalnya:
   ```
   /opt/odoo16/custom-addons/waf_security
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

## Contoh Skenario Latihan untuk Murid

1. Coba akses `/web?x=<script>alert(1)</script>` pada instance dev lokal,
   lihat apakah tercatat di Audit Log sebagai `xss`.
2. Ubah `block_mode` ke `monitor`, ulangi request yang sama, amati bedanya
   (tidak diblokir, hanya dicatat).
3. Coba login gagal berkali-kali dan amati kapan IP otomatis di-ban.
4. Tambahkan pattern regex baru di `waf_detection_engine.py` lalu uji.
