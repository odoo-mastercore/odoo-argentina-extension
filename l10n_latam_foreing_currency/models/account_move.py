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
    amount_untaxed_signed_foreign = fields.Monetary(string='Untaxed Amount Signed', readonly=True, currency_field='company_foreign_currency_id')

    @api.depends('amount_total_signed', 'amount_residual', 'amount_untaxed_signed')
    def _compute_foreigns(self):
        for rec in self:
            if rec.move_type in ['out_invoice','out_refund','in_invoice','in_refund'] and not rec.debit_origin_id:
                _logger.warning('if rec.move_type')
                if rec.currency_id == rec.company_foreign_currency_id:
                    rec.amount_total_signed_foreign = rec.amount_total_in_currency_signed
                    rec.amount_residual_foreign = rec.amount_residual
                    rec.amount_untaxed_signed_foreign = rec.amount_untaxed_signed
                else:
                    rec.amount_total_signed_foreign = rec.currency_id._convert(rec.amount_total_in_currency_signed, rec.company_foreign_currency_id, rec.company_id, rec.date)
                    rec.amount_residual_foreign = rec.currency_id._convert(rec.amount_residual, rec.company_foreign_currency_id, rec.company_id, rec.date)
                    rec.amount_untaxed_signed_foreign = rec.currency_id._convert(rec.amount_untaxed_signed, rec.company_foreign_currency_id, rec.company_id, rec.date)
            else:
                _logger.warning('nota de debito')
                rec.amount_total_signed_foreign = 0
                rec.amount_residual_foreign = 0
                rec.amount_untaxed_signed_foreign = 0
