# -*- coding: utf-8 -*-
{
    'name': 'WAF Security - Web Application Firewall',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Web Application Firewall untuk Odoo 18 ',
    'price': 4.9,
    'currency': 'EUR',
    'description': """
WAF Security for Odoo 18
=========================
Modul Web Application Firewall (WAF)
yang terintegrasi langsung di dalam Odoo.

Fitur:
------
* Request Inspection (setiap request masuk diperiksa)
* SQL Injection Detection
* XSS (Cross Site Scripting) Detection
* RCE (Remote Code Execution) Detection
* Path Traversal Detection
* IP Whitelist / Blacklist
* Rate Limiting
* Brute Force Protection (login)
* Security Headers (CSP, HSTS, X-Frame-Options, dll)
* Audit Log lengkap
* Dashboard Monitoring
* Auto Ban IP mencurigakan
* Alert via Email & Telegram
* Subscription Monitor - kirim status instance (versi, jumlah user,
  tanggal expired) ke dashboard eksternal yang dikonfigurasi admin
  (opsional, OFF secara default)

CATATAN PENTING (untuk pembelajaran):
--------------------------------------
Modul ini adalah untuk memahami
cara kerja WAF berbasis signature/regex. Modul ini BUKAN pengganti WAF
production-grade (seperti ModSecurity, Cloudflare WAF, AWS WAF, dsb).
Untuk deployment production sesungguhnya, tetap gunakan WAF di layer
reverse proxy/network (Nginx + ModSecurity, Cloudflare, dll) sebagai
lapisan pertama, dan modul ini sebagai lapisan tambahan (defense in depth).

Fitur Subscription Monitor NONAKTIF secara default dan memerlukan
konfigurasi eksplisit (URL & API key milik Anda sendiri) sebelum aktif -
lihat README.md. Pastikan Anda memahami data apa yang dikirim dan ke mana
sebelum mengaktifkannya.
    """,
    'author': 'Senja Techno',
    'website': 'https://odoo.my.id',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'data': [
        'security/waf_security_groups.xml',
        'security/ir.model.access.csv',
        'data/waf_cron.xml',
        'data/waf_default_data.xml',
        'views/waf_config_views.xml',
        'views/waf_log_views.xml',
        'views/waf_ip_rule_views.xml',
        'views/waf_dashboard_views.xml',
        'views/waf_subscription_monitor_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
