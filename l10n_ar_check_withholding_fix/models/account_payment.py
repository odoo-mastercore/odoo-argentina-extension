# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
# See https://www.gnu.org/licenses/agpl-3.0.html
#
##############################################################################

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _prepare_move_lines_per_type(self, write_off_line_vals=None, force_balance=None):
        res = super()._prepare_move_lines_per_type(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
        )

        wth_lines = res.get("withholding_lines", [])
        if not wth_lines:
            return res

        has_checks = self.l10n_latam_new_check_ids | self.l10n_latam_move_check_ids
        if not has_checks:
            return res

        wth_balance = sum(line["balance"] for line in wth_lines)
        raw_wth_amount_currency = sum(line["amount_currency"] for line in wth_lines)

        counterpart_is_foreign = (
            self.currency_id == self.company_id.currency_id
            and self.counterpart_currency_id
            and self.counterpart_currency_id != self.company_currency_id
        )

        if self.currency_id != self.company_id.currency_id:
            conversion_rate = self.accounting_rate or 1.0
            wth_amount_currency_pay = self.currency_id.round(wth_balance * conversion_rate)
        else:
            conversion_rate = 1.0
            wth_amount_currency_pay = raw_wth_amount_currency

        foreign_journal = self.currency_id != self.company_id.currency_id

        liquidity_lines = res.get("liquidity_lines", [])
        if liquidity_lines:
            if foreign_journal:
                sign = -1 if self.payment_type == "outbound" else 1
                liquidity_lines[0]["amount_currency"] = sign * self.amount
                liquidity_lines[0]["balance"] = liquidity_lines[0]["amount_currency"] / conversion_rate
            else:
                liquidity_lines[0]["balance"] += wth_balance
                liquidity_lines[0]["amount_currency"] += wth_amount_currency_pay

            if self.company_currency_id.is_zero(liquidity_lines[0]["balance"]):
                res["liquidity_lines"] = []

        counterpart_lines = res.get("counterpart_lines", [])
        if counterpart_lines:
            if foreign_journal:
                wo_balance = sum(line["balance"] for line in res.get("write_off_lines", []))
                liq_balance = sum(line["balance"] for line in liquidity_lines) if liquidity_lines else 0
                counterpart_lines[0]["balance"] = -liq_balance - wo_balance - wth_balance
            else:
                counterpart_lines[0]["balance"] -= wth_balance

            if not counterpart_is_foreign and not (
                self.counterpart_currency_id and self.counterpart_currency_id != self.currency_id
            ):
                counterpart_lines[0]["amount_currency"] -= wth_amount_currency_pay

            if counterpart_lines[0].get("currency_id") == self.company_currency_id.id:
                counterpart_lines[0]["amount_currency"] = counterpart_lines[0]["balance"]

        return res
