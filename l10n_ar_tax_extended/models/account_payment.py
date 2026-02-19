# -*- coding: utf-8 -*-
################################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
################################################################################
from odoo import api, models, fields, _, Command
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    withholding_amount_currency = fields.Float(
        string="Retención en divisa",
        compute="_compute_withholding_amount_currency",
        store=True
    )

    @api.depends("l10n_ar_withholding_line_ids")
    def _compute_withholding_amount_currency(self):
        for payment in self:
            payment.withholding_amount_currency = sum(payment.l10n_ar_withholding_line_ids.mapped('amount_currency'))

    @api.depends(
        "currency_id", "company_id", "l10n_ar_withholding_line_ids", "destination_account_id", "counterpart_currency_id"
    )
    def _compute_withholding_warning(self):
        for rec in self:
            if not rec.company_id.enabled_retention_currency:
                return super()._check_withholdings_and_currency()
            pass

    def _prepare_witholding_write_off_vals(self):
        res = super()._prepare_witholding_write_off_vals()
        for line in self.l10n_ar_withholding_line_ids:
            if line.amount_currency and line.foreign_currency_id and res:
                for i in range(len(res)):
                    if res[i]['name'] == line.name:
                        amount = line.amount_currency
                        if res[i]['amount_currency'] < 0:
                            amount = -abs(line.amount_currency)
                        res[i].update({
                            'currency_id': line.foreign_currency_id.id,
                            'amount_currency': amount
                        })
        return res

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        res = super(AccountPayment, self)._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance
        )
        # Lo dejamos asi para que funcione con cualquier pago con moneda en divisas
        if self.counterpart_currency_id and self.counterpart_currency_amount:
            for i in range(len(res)):
                keys = {'credit', 'debit'}
                if keys.issubset(res[i].keys()):
                    amount = self.counterpart_currency_amount
                    if self.withholding_amount_currency:
                        account_id = self.env['account.account'].browse(res[i]['account_id'])
                        if account_id.account_type not in ('asset_receivable', 'liability_payable'):
                            amount -= self.withholding_amount_currency
                    if res[i]['credit'] > 0.0:
                        res[i].update({
                            'currency_id': self.counterpart_currency_id.id,
                            'amount_currency': -abs(amount)
                        })
                    if res[i]['debit'] > 0.0:
                        res[i].update({
                            'currency_id': self.counterpart_currency_id.id,
                            'amount_currency': abs(amount)
                        })
        return res

    @api.depends("l10n_ar_fiscal_position_id", "partner_id", "company_id", "date")
    def _compute_l10n_ar_withholding_line_ids(self):
        """
            Este metodo unifica la logica entre l10n_ar_withholding y l10n_ar_tax_extended
            manteniendo prioridad a la configuracion de la posicion fiscal.
        """
        for rec in self.filtered(lambda x: x.partner_type == "supplier"):
            date = rec.date or fields.Date.context_today(self)
            withholdings = [Command.clear()]
            if rec.l10n_ar_fiscal_position_id.l10n_ar_tax_ids:
                taxes = rec.l10n_ar_fiscal_position_id._l10n_ar_add_taxes(
                    rec.partner_id, rec.company_id, date, "withholding"
                )
                withholdings += [Command.create({"tax_id": x.id}) for x in taxes]
            else:
                partner_taxes = self.env['l10n_ar.partner.tax'].search([
                    *self.env['l10n_ar.partner.tax']._check_company_domain(rec.company_id),
                    '|', ('from_date', '>=', date), ('from_date', '=', False),
                    '|', ('to_date', '<=', date), ('to_date', '=', False),
                    ('partner_id', '=', rec.partner_id.commercial_partner_id.id),
                    ('tax_id.l10n_ar_withholding_payment_type', '=', rec.partner_type)
                ])
                withholdings = [Command.clear()] + [Command.create({'tax_id': x.tax_id.id}) for x in partner_taxes]
            rec.l10n_ar_withholding_line_ids = withholdings