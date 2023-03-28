###############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2020-Present.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class AccountPaymentGroup(models.Model):

    _inherit = "account.payment.group"

    #This field is to be used by invoice in multicurrency
    selected_finacial_debt = fields.Monetary(
        string='Selected Financial Debt',
        compute='_compute_selected_debt_financial',
    )
    selected_finacial_debt_currency = fields.Monetary(
        string='Selected Financial Debt in foreign currency',
        compute='_compute_selected_debt_financial',
    )
    debt_multicurrency = fields.Boolean(
        string='debt is in foreign currency?', default=False,
    )
    selected_debt_currency_id = fields.Many2one("res.currency",
        string='Selected Debt in foreign currency',
    )
    apply_foreign_payment = fields.Boolean('Aplicar Marcador de Tipo de cambio')
    exchange_rate_applied = fields.Float('Tasa de Cambio')
    @api.depends(
        'to_pay_move_line_ids.amount_residual',
        'to_pay_move_line_ids.amount_residual_currency',
        'to_pay_move_line_ids.currency_id',
        'to_pay_move_line_ids.move_id',
        'payment_date',
        'currency_id',
        'partner_id',
        'selected_debt',
    )
    def _compute_selected_debt_financial(self):
        for rec in self:
            selected_finacial_debt = 0.0
            selected_finacial_debt_currency = 0.0
            for line in rec.to_pay_move_line_ids._origin:
                # factor for total_untaxed
                if line.move_id.currency_id.id != rec.company_id.currency_id.id:
                    selected_finacial_debt_currency += line.amount_residual_currency
                    rec.debt_multicurrency = True
                    rec.selected_debt_currency_id = line.move_id.currency_id.id
                elif line.move_id.currency_id.id != rec.company_id.currency_id.id and rec.debt_multicurrency:
                    selected_finacial_debt_currency += line.amount_residual_currency
                    rec.debt_multicurrency = True
                else:
                    rec.debt_multicurrency = False
                if rec.debt_multicurrency:
                    last_rate = 0
                    last_rate = self.env['res.currency.rate'].search([
                        ('currency_id', '=', rec.selected_debt_currency_id.id),
                        ('name', '=', rec.payment_date)
                    ], limit=1).rate
                    if last_rate == 0:
                        last_rate = self.env['res.currency.rate'].search([
                            ('currency_id', '=', rec.selected_debt_currency_id.id),
                        ], limit=1).rate
                    if last_rate == 0:
                        last_rate = 1
                    rate = round((1 / last_rate), 4)
                    finacial_debt_currency = selected_finacial_debt_currency*rate
                    selected_finacial_debt += finacial_debt_currency
                else:
                    selected_finacial_debt += line.amount_residual
                    #selected_debt += line.move_id.amount_residual
            sign = rec.partner_type == 'supplier' and -1.0 or 1.0
            rec.selected_finacial_debt = selected_finacial_debt * sign
            rec.selected_finacial_debt_currency = selected_finacial_debt_currency * sign

    @api.depends('selected_debt', 'debt_multicurrency','selected_finacial_debt', 'unreconciled_amount',)
    def _compute_to_pay_amount(self):
        for rec in self:
            if rec.selected_finacial_debt != rec.selected_debt:
                rec.to_pay_amount = rec.selected_finacial_debt + rec.unreconciled_amount
            else:
                rec.to_pay_amount = rec.selected_debt + rec.unreconciled_amount

    @api.onchange('to_pay_amount')
    def _inverse_to_pay_amount(self):
        for rec in self:
            if rec.selected_finacial_debt != rec.selected_debt:
                rec.unreconciled_amount = rec.to_pay_amount - rec.selected_finacial_debt
            else:
                rec.unreconciled_amount = rec.to_pay_amount - rec.selected_debt
