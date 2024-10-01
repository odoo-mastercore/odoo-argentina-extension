#-*- coding: utf-8 -*-
from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    rate_dummy = fields.Float(string="Tasa", digits=(16,6), compute='_compute_rate_dummy', store=False)

    @api.depends('currency_id', 'company_id', 'date', 'invoice_date')
    def _compute_rate_dummy(self):
        for rec in self:
            rec.rate_dummy = 0.0
            if rec.company_id.currency_id.id == rec.currency_id.id:
                _logger.info('***ENTRAR**')
                country=self.env['res.country'].search([('code','=','AR')])
                rec.rate_dummy = self.env['res.currency']._get_conversion_rate(rec.company_id.foreign_currency_id,
                                                                               country.currency_id,
                                                                                rec.company_id,
                                                                                rec.date if rec.invoice_date \
                                                                                else fields.Date.context_today(rec))
                _logger.info('***ENTRAR COMPUTADO--->%s**'%(rec.computed_currency_rate))