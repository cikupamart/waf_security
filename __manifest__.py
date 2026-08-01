# -*- coding: utf-8 -*-
{
    'name': 'WAF Security - Web Application Firewall',
    'version': '16.0.1.0.0',
    'category': 'Tools',
    'summary': 'Web Application Firewall untuk Odoo 16 (Educational Purpose)',
    'price': 20.99,
    'currency': 'EUR',
    'description': """

WAF Security for Odoo 16
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

CATATAN PENTING :
--------------------------------------
Modul ini adalah alat bantu (tool) untuk memahami
cara kerja WAF berbasis signature/regex. Modul ini BUKAN pengganti WAF
production-grade (seperti ModSecurity, Cloudflare WAF, AWS WAF, dsb).
Untuk deployment production sesungguhnya, tetap gunakan WAF di layer
reverse proxy/network (Nginx + ModSecurity, Cloudflare, dll) sebagai
lapisan pertama, dan modul ini sebagai lapisan tambahan (defense in depth).
    """,
    'author': 'Senja Techno',
    'website': 'https://odoo.my.id',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/waf_security_groups.xml',
        'security/ir.model.access.csv',
        'data/waf_cron.xml',
        'data/waf_default_data.xml',
        'views/waf_config_views.xml',
        'views/waf_log_views.xml',
        'views/waf_ip_rule_views.xml',
        'views/waf_dashboard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
