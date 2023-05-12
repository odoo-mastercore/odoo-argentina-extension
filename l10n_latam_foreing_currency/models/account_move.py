from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, frozendict
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    company_foreign_currency_id = fields.Many2one(string='Foreign Company Currency', readonly=True,
        related='company_id.foreign_currency_id')
    amount_total_signed_foreign = fields.Monetary(string='Total Signed', readonly=True, currency_field='company_foreign_currency_id')
    amount_residual_foreign = fields.Monetary(string='Amount Due', currency_field='company_foreign_currency_id')

    @api.depends('amount_total_signed', 'amount_residual')
    def _compute_foreigns(self):
        for rec in self:
            if rec.move_type in ['out_invoice','out_refund','in_invoice','in_refund'] and not rec.debit_origin_id:
                _logger.warning('if rec.move_type')
                if rec.currency_id == rec.company_foreign_currency_id:
                    _logger.warning('ec.currency_id')
                    rec.amount_total_signed_foreign = rec.amount_total_in_currency_signed
                    rec.amount_residual_foreign = rec.amount_residual
                else:
                    _logger.warning('ec.else')
                    if rec.currency_id == rec.company_id.currency_id:
                        _logger.warning('ec.kskkss')
                        rate = 1/rec.l10n_ar_currency_rate
                    else:
                        _logger.warning('ec.jskjsjkskelse')
                        rate = rec.env['res.currency.rate'].search([
                            ('currency_id','=', rec.company_foreign_currency_id.id),
                            ('name', '<=', rec.invoice_date)], limit=1).inverse_company_rate

                    rec.amount_total_signed_foreign = rec.amount_total_in_currency_signed / rate
                    rec.amount_residual_foreign = rec.amount_residual / rate
            
            else:    
                _logger.warning('nota de debito')
                rec.amount_total_signed_foreign = 0
                rec.amount_residual_foreign = 0
