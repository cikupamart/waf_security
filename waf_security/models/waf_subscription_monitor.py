# -*- coding: utf-8 -*-
import json
import logging
import uuid

from odoo import api, fields, models, release
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


class WafSubscriptionLog(models.Model):
    _name = 'waf.subscription.log'
    _description = 'WAF Subscription Monitor - Sync Log'
    _order = 'create_date desc'

    name = fields.Char(string='Ringkasan', default='Sync ke dashboard')
    state = fields.Selection([
        ('success', 'Sukses'),
        ('error', 'Gagal'),
    ], string='Status', required=True)
    http_status = fields.Char(string='HTTP Status')
    payload = fields.Text(string='Payload Terkirim')
    response = fields.Text(string='Response Server')
    create_date = fields.Datetime(string='Waktu', readonly=True)


class WafSubscriptionMonitor(models.AbstractModel):
    """Kumpulan logic untuk mengambil data instance dan mengirimnya
    ke dashboard eksternal (mis. dashboard milik partner/MSP yang
    mengelola instance ini).

    Model ini abstract (tidak menyimpan record), dipanggil dari cron
    maupun tombol manual di Settings.

    CATATAN PRIVASI - PENTING:
    -----------------------------
    Data yang dikirim bisa mencakup daftar user internal (nama, login,
    waktu login terakhir) jika opsi `waf_security.subscription_monitor
    .include_user_list` diaktifkan. Data ini adalah PII (Personally
    Identifiable Information) karyawan. Pastikan:
    1. Admin instance SADAR dan SETUJU fitur ini aktif serta ke mana
       data dikirim (URL dashboard dikonfigurasi eksplisit di Settings,
       bukan hardcoded).
    2. Kalau tidak benar-benar perlu detail per-user, biarkan toggle
       "include_user_list" nonaktif - default-nya memang OFF, dan sync
       hanya mengirim ringkasan agregat (jumlah user, dsb), bukan nama/
       email individual.
    3. Cek regulasi privasi data yang berlaku (mis. UU PDP di Indonesia,
       atau GDPR jika ada user/data subject di Eropa) sebelum mengaktifkan
       pengiriman data personal ke pihak ketiga.
    """
    _name = 'waf.subscription.monitor'
    _description = 'WAF Subscription Monitor - Core Logic'

    # ---------------------------------------------------------------
    # Helpers konfigurasi
    # ---------------------------------------------------------------
    @api.model
    def _get_param(self, key, default=False):
        return self.env['ir.config_parameter'].sudo().get_param(key, default)

    @api.model
    def _set_param(self, key, value):
        return self.env['ir.config_parameter'].sudo().set_param(key, value)

    @api.model
    def _get_instance_uuid(self):
        """UUID unik & persisten per database, dibuat sekali saja."""
        uid = self._get_param('waf_security.subscription_monitor.instance_uuid')
        if not uid:
            uid = str(uuid.uuid4())
            self._set_param('waf_security.subscription_monitor.instance_uuid', uid)
        return uid

    @api.model
    def _is_enterprise(self):
        return bool(self.env['ir.module.module'].sudo().search_count([
            ('name', '=', 'web_enterprise'),
            ('state', '=', 'installed'),
        ]))

    # ---------------------------------------------------------------
    # Pengumpulan data instance
    # ---------------------------------------------------------------
    @api.model
    def _collect_instance_data(self):
        icp = self.env['ir.config_parameter'].sudo()
        Users = self.env['res.users'].sudo()

        active_user_count = Users.search_count([
            ('active', '=', True),
            ('share', '=', False),  # exclude portal/public user
        ])
        total_user_count = Users.search_count([('active', '=', True)])

        companies = self.env['res.company'].sudo().search([])

        data = {
            'instance_uuid': self._get_instance_uuid(),
            'database_name': self.env.cr.dbname,
            'domain': icp.get_param('web.base.url'),
            'odoo_version': release.version,
            'edition': 'enterprise' if self._is_enterprise() else 'community',
            'active_internal_users': active_user_count,
            'active_total_users': total_user_count,
            'companies': [{
                'name': c.name,
                'country': c.country_id.name or '',
            } for c in companies],
            'main_company': self.env.company.name,
            # Field standar Odoo Enterprise untuk tanggal kadaluarsa subscription.
            # Untuk Community, field ini biasanya kosong; boleh diisi manual lewat
            # Settings > WAF Security > Subscription Monitor > Manual Expiration Date.
            'subscription_expiration_date': (
                icp.get_param('database.expiration_date')
                or icp.get_param('waf_security.subscription_monitor.manual_expiration_date')
                or False
            ),
            'installed_apps_count': self.env['ir.module.module'].sudo().search_count(
                [('state', '=', 'installed')]
            ),
        }

        # Daftar user internal (nama, login, waktu login terakhir) HANYA
        # dikirim jika admin secara eksplisit mengaktifkan opsi ini.
        # Default: OFF (lihat catatan privasi di docstring class ini).
        include_user_list = self._get_param(
            'waf_security.subscription_monitor.include_user_list', 'False')
        if include_user_list in ('True', True, '1', 1):
            internal_users = Users.search([
                ('active', '=', True),
                ('share', '=', False),
            ])
            data['user_logins'] = [{
                'name': u.name,
                'login': u.login,
                'last_login': u.login_date.strftime('%Y-%m-%d %H:%M:%S') if u.login_date else False,
            } for u in internal_users]

        return data

    # ---------------------------------------------------------------
    # Pengiriman ke dashboard
    # ---------------------------------------------------------------
    @api.model
    def sync_now(self, raise_on_error=False):
        """Kumpulkan data instance dan kirim ke dashboard eksternal.
        Dipanggil dari cron maupun tombol manual.
        """
        if requests is None:
            _logger.error("Library 'requests' tidak tersedia di environment ini.")
            if raise_on_error:
                raise UserError("Library 'requests' tidak tersedia di server Odoo.")
            return False

        enabled = self._get_param('waf_security.subscription_monitor.enabled', 'False')
        api_url = self._get_param('waf_security.subscription_monitor.api_url')
        api_key = self._get_param('waf_security.subscription_monitor.api_key')

        if enabled not in ('True', True, '1', 1) and not raise_on_error:
            # Sync manual (raise_on_error=True) tetap boleh jalan walau belum
            # di-enable, untuk keperluan test koneksi.
            return False

        if not api_url or not api_key:
            msg = 'URL Dashboard atau API Key belum dikonfigurasi.'
            _logger.warning(msg)
            self.env['waf.subscription.log'].sudo().create({
                'state': 'error',
                'response': msg,
            })
            if raise_on_error:
                raise UserError(msg)
            return False

        payload = self._collect_instance_data()

        try:
            resp = requests.post(
                api_url,
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer %s' % api_key,
                },
                timeout=15,
            )
            log_vals = {
                'payload': json.dumps(payload, indent=2, ensure_ascii=False),
                'http_status': str(resp.status_code),
            }
            if 200 <= resp.status_code < 300:
                log_vals.update({
                    'state': 'success',
                    'response': resp.text[:5000],
                })
                self.env['waf.subscription.log'].sudo().create(log_vals)
                return True
            else:
                log_vals.update({
                    'state': 'error',
                    'response': resp.text[:5000],
                })
                self.env['waf.subscription.log'].sudo().create(log_vals)
                if raise_on_error:
                    raise UserError(
                        'Gagal mengirim data ke dashboard (HTTP %s): %s'
                        % (resp.status_code, resp.text[:500])
                    )
                return False
        except requests.exceptions.RequestException as e:
            _logger.exception('Gagal terhubung ke dashboard monitoring')
            self.env['waf.subscription.log'].sudo().create({
                'payload': json.dumps(payload, indent=2, ensure_ascii=False),
                'state': 'error',
                'response': str(e)[:5000],
            })
            if raise_on_error:
                raise UserError('Gagal terhubung ke dashboard: %s' % e)
            return False

    @api.model
    def _cron_sync(self):
        """Entry point untuk scheduled action."""
        self.sync_now(raise_on_error=False)
