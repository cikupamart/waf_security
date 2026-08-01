# -*- coding: utf-8 -*-
import logging
import json
import urllib.request

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class WafLog(models.Model):
    _name = 'waf.log'
    _description = 'WAF Audit Log'
    _order = 'create_date desc'
    _rec_name = 'display_name_computed'

    ip_address = fields.Char(string='Alamat IP', index=True)
    user_id = fields.Many2one('res.users', string='User')
    url = fields.Char(string='URL')
    method = fields.Char(string='HTTP Method')
    threat_type = fields.Selection([
        ('sql_injection', 'SQL Injection'),
        ('xss', 'XSS'),
        ('rce', 'RCE / Command Injection'),
        ('path_traversal', 'Path Traversal'),
        ('rate_limit', 'Rate Limit Exceeded'),
        ('brute_force', 'Brute Force Login'),
        ('blacklisted', 'Blacklisted IP'),
        ('other', 'Lainnya'),
    ], string='Jenis Ancaman', index=True)
    severity = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ], string='Severity', default='medium', index=True)
    matched_pattern = fields.Char(string='Pattern yang Cocok')
    matched_payload = fields.Text(string='Payload Terdeteksi')
    source_field = fields.Char(string='Sumber (Parameter/Header)')
    request_snippet = fields.Text(string='Cuplikan Request')
    action_taken = fields.Selection([
        ('logged', 'Hanya Dicatat'),
        ('blocked', 'Diblokir'),
        ('banned', 'IP Di-ban'),
    ], string='Tindakan', default='logged')
    user_agent = fields.Char(string='User Agent')

    display_name_computed = fields.Char(compute='_compute_display_name', store=False)

    @api.depends('ip_address', 'threat_type')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name_computed = f"[{rec.threat_type or '-'}] {rec.ip_address or '-'}"

    @api.model
    def log_event(self, ip_address=None, user_id=None, url=None, method=None,
                  threat_type='other', severity='medium', matched_pattern=None,
                  matched_payload=None, source_field=None, request_snippet=None,
                  action_taken='logged', user_agent=None):
        """Entry point utama untuk mencatat event WAF dan memicu alert bila perlu."""
        vals = {
            'ip_address': ip_address,
            'user_id': user_id,
            'url': url,
            'method': method,
            'threat_type': threat_type,
            'severity': severity,
            'matched_pattern': matched_pattern,
            'matched_payload': matched_payload,
            'source_field': source_field,
            'request_snippet': request_snippet,
            'action_taken': action_taken,
            'user_agent': user_agent,
        }
        log = self.sudo().create(vals)
        try:
            log._maybe_send_alert()
        except Exception:
            _logger.exception("WAF: gagal mengirim alert")
        return log

    def _maybe_send_alert(self):
        self.ensure_one()
        config = self.env['waf.config'].sudo().get_active_config()
        if not config:
            return

        severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        min_severity = severity_order.get(config.alert_min_severity, 2)
        current_severity = severity_order.get(self.severity, 0)
        if current_severity < min_severity:
            return

        subject = f"[WAF ALERT] {self.threat_type} terdeteksi dari IP {self.ip_address}"
        body = (
            f"Waktu: {self.create_date}\n"
            f"IP: {self.ip_address}\n"
            f"URL: {self.url}\n"
            f"Method: {self.method}\n"
            f"Jenis Ancaman: {self.threat_type}\n"
            f"Severity: {self.severity}\n"
            f"Tindakan: {self.action_taken}\n"
            f"Pattern: {self.matched_pattern}\n"
            f"Payload: {self.matched_payload}\n"
        )

        if config.enable_email_alert and config.alert_email_to:
            self._send_email_alert(config, subject, body)

        if config.enable_telegram_alert and config.telegram_bot_token and config.telegram_chat_id:
            self._send_telegram_alert(config, subject + "\n\n" + body)

    def _send_email_alert(self, config, subject, body):
        try:
            mail_values = {
                'subject': subject,
                'body_html': f"<pre>{body}</pre>",
                'email_to': config.alert_email_to,
                'auto_delete': True,
            }
            self.env['mail.mail'].sudo().create(mail_values).send()
        except Exception:
            _logger.exception("WAF: gagal mengirim email alert")

    def _send_telegram_alert(self, config, text):
        """Kirim alert ke Telegram menggunakan Bot API.
        Menggunakan urllib bawaan agar tidak menambah dependency eksternal.
        """
        try:
            url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
            data = json.dumps({
                'chat_id': config.telegram_chat_id,
                'text': text[:4000],
            }).encode('utf-8')
            req = urllib.request.Request(
                url, data=data, headers={'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            _logger.exception("WAF: gagal mengirim telegram alert")

    @api.model
    def cron_cleanup_old_logs(self):
        """Dipanggil oleh scheduled action untuk membersihkan log lama."""
        config = self.env['waf.config'].sudo().get_active_config()
        retention_days = config.log_retention_days if config else 90
        if retention_days <= 0:
            return
        threshold = fields.Datetime.now() - __import__('datetime').timedelta(days=retention_days)
        old_logs = self.sudo().search([('create_date', '<', threshold)])
        old_logs.unlink()
