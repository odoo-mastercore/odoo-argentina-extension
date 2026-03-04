# -*- coding: utf-8 -*-
################################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
################################################################################
from odoo import api, models, fields, Command


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
        payments_with_standard_warning = self.filtered(lambda rec: not rec.company_id.enabled_retention_currency)
        super(AccountPayment, payments_with_standard_warning)._compute_withholding_warning()
        (self - payments_with_standard_warning).withholding_warning = False

    def _prepare_move_lines_per_type(self, write_off_line_vals=None, force_balance=None):
        """Adjust move lines when retentions in foreign currency are enabled.

        In Odoo 18, payment move synchronization is based on
        ``_prepare_move_lines_per_type``. If the payment uses counterpart
        currency, we keep outstanding and withholding tax lines in that
        currency so the generated move is consistent in create/write flows.
        """
        res = super()._prepare_move_lines_per_type(write_off_line_vals=write_off_line_vals, force_balance=force_balance)
        if not (
            self.company_id.enabled_retention_currency
            and self._use_counterpart_currency()
            and self.counterpart_currency_id
        ):
            return res

        counterpart_currency = self.counterpart_currency_id
        withholding_lines = self.l10n_ar_withholding_line_ids
        withholding_amount_currency = sum(withholding_lines.mapped("amount_currency"))
        if not withholding_lines:
            return res

        # Outstanding line in counterpart currency: net amount in divisa.
        liquidity_lines = res.get("liquidity_lines", [])
        if liquidity_lines:
            liquidity_sign = 1 if liquidity_lines[0].get("balance", 0.0) >= 0.0 else -1
            liquidity_amount_currency = counterpart_currency.round(
                self.counterpart_currency_amount - withholding_amount_currency
            )
            liquidity_lines[0].update({
                "currency_id": counterpart_currency.id,
                "amount_currency": liquidity_sign * abs(liquidity_amount_currency),
            })

        # Withholding tax lines in counterpart currency.
        withholding_amount_by_name = {
            line.name: counterpart_currency.round(line.amount_currency)
            for line in withholding_lines
            if line.name and line.amount_currency
        }
        for move_line_vals in res.get("withholding_lines", []):
            if not move_line_vals.get("tax_repartition_line_id"):
                continue
            amount_currency = withholding_amount_by_name.get(move_line_vals.get("name"))
            if amount_currency is None:
                continue
            sign = -1 if move_line_vals.get("balance", 0.0) < 0.0 else 1
            move_line_vals.update({
                "currency_id": counterpart_currency.id,
                "amount_currency": sign * abs(amount_currency),
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
