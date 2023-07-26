from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, frozendict
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    company_foreign_currency_id = fields.Many2one(
        string='Foreign Company Currency', readonly=True,
        related='company_id.foreign_currency_id'
    )
    amount_total_foreign = fields.Monetary(string='Total en Divisa',
        readonly=True, currency_field='company_foreign_currency_id'
    )
    amount_residual_foreign = fields.Monetary(string='Adeudado en Divisa',
        currency_field='company_foreign_currency_id'
    )
    amount_untaxed_foreign = fields.Monetary(string='Subtotal en Divisa',
        readonly=True, currency_field='company_foreign_currency_id'
    )

    @api.depends('amount_total', 'amount_residual', 'amount_untaxed')
    def _compute_foreigns(self):
        for rec in self:
            if rec.move_type in ['out_invoice','out_refund','in_invoice','in_refund'] and not rec.debit_origin_id:
                _logger.warning('Factura')
                if rec.currency_id == rec.company_foreign_currency_id:
                    rec.amount_total_foreign = rec.amount_total
                    rec.amount_residual_foreign = rec.amount_residual
                    rec.amount_untaxed_foreign = rec.amount_untaxed
                else:
                    rec.amount_total_foreign = rec.currency_id._convert(
                        rec.amount_total, rec.company_foreign_currency_id,
                        rec.company_id, rec.date)
                    rec.amount_residual_foreign = rec.currency_id._convert(
                        rec.amount_residual, rec.company_foreign_currency_id,
                        rec.company_id, rec.date)
                    rec.amount_untaxed_foreign = rec.currency_id._convert(
                        rec.amount_untaxed, rec.company_foreign_currency_id,
                        rec.company_id, rec.date)
            else:
                _logger.warning('nota de debito')
                rec.amount_total_foreign = 0
                rec.amount_residual_foreign = 0
                rec.amount_untaxed_foreign = 0


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    company_foreign_currency_id = fields.Many2one(
        string='Foreign Company Currency', readonly=True,
        related='company_id.foreign_currency_id'
    )
    price_subtotal_foreign = fields.Monetary('Precio Subtotal en Divisa',
        currency_field='company_foreign_currency_id'
    )

    @api.depends('product_id','quantity','price_subtotal', 'move_id.amount_untaxed')
    def _compute_line_foreigns(self):
        for rec in self:
            if rec.product_id:
                if rec.move_id.move_type in ['out_invoice','in_refund'] and not rec.move_id.debit_origin_id:
                    _logger.warning('Factura')
                    if rec.currency_id == rec.company_foreign_currency_id:
                        rec.price_subtotal_foreign = rec.price_subtotal
                    else:
                        rec.price_subtotal_foreign = rec.currency_id._convert(
                            rec.price_subtotal, rec.company_foreign_currency_id,
                            rec.company_id, rec.date)
                elif rec.move_id.move_type in ['out_refund','in_invoice'] and not rec.move_id.debit_origin_id:
                    _logger.warning('NotaC')
                    if rec.currency_id == rec.company_foreign_currency_id:
                        rec.price_subtotal_foreign = -1 * rec.price_subtotal
                    else:
                        rec.price_subtotal_foreign = -1 * (rec.currency_id._convert(
                            rec.price_subtotal, rec.company_foreign_currency_id,
                            rec.company_id, rec.date))
                else:
                    _logger.warning('nota de debito')
                    rec.price_subtotal_foreign = 0


