# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
# See https://www.gnu.org/licenses/agpl-3.0.html
#
##############################################################################

from datetime import date

from odoo import fields, models


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_ar_social_security_deposit_period = fields.Char(
        string="Social Security Deposit Period",
        help="Period of the latest social security contribution deposit, as required by Decree-Law 17.250/67.",
    )
    l10n_ar_social_security_deposit_date = fields.Date(
        string="Social Security Deposit Date",
        help="Date of the latest social security contribution deposit, as required by Decree-Law 17.250/67.",
    )
    l10n_ar_social_security_bank = fields.Char(
        string="Social Security Deposit Bank",
        help="Bank used for the latest social security contribution deposit, as required by Decree-Law 17.250/67.",
    )

    def _l10n_ar_get_semester_dates(self):
        self.ensure_one()
        if not self.date_to:
            return False, False
        if self.date_to.month <= 6:
            return date(self.date_to.year, 1, 1), date(self.date_to.year, 6, 30)
        return date(self.date_to.year, 7, 1), date(self.date_to.year, 12, 31)

    def _l10n_ar_get_seniority_date(self):
        self.ensure_one()
        return (
            self.version_id.l10n_ar_seniority_date
            or self.version_id.date_start
            or self.version_id.contract_date_start
        )

    def _l10n_ar_get_seniority_years(self, at_date=False):
        self.ensure_one()
        at_date = at_date or self.date_to or fields.Date.today()
        seniority_date = self._l10n_ar_get_seniority_date()
        if not seniority_date or at_date < seniority_date:
            return 0
        return (at_date - seniority_date).days // 365

    def _l10n_ar_get_vacation_days(self):
        self.ensure_one()
        seniority_years = self._l10n_ar_get_seniority_years()
        if seniority_years < 5:
            return 14
        if seniority_years < 10:
            return 21
        if seniority_years < 20:
            return 28
        return 35

    def _l10n_ar_compute_vacation_amount(self, vacation_days):
        self.ensure_one()
        divisor = self._rule_parameter("l10n_ar_vacation_divisor") or 25.0
        wage = self.version_id.wage or self.paid_amount
        return (wage / divisor) * vacation_days if divisor else 0.0

    def _l10n_ar_get_sac_base(self):
        self.ensure_one()
        semester_start, semester_end = self._l10n_ar_get_semester_dates()
        if not semester_start:
            return 0.0
        semester_slips = self.env["hr.payslip"].search([
            ("employee_id", "=", self.employee_id.id),
            ("state", "in", ("done", "paid")),
            ("date_from", ">=", semester_start),
            ("date_to", "<=", semester_end),
        ])
        if self.id:
            semester_slips -= self
        gross_totals = semester_slips.line_ids.filtered(lambda line: line.code == "GROSS").mapped("total")
        best_remuneration = max(gross_totals, default=0.0)
        return best_remuneration or self.version_id.wage or self.paid_amount

    def _l10n_ar_get_sac_proportional_ratio(self):
        self.ensure_one()
        semester_start, semester_end = self._l10n_ar_get_semester_dates()
        if not semester_start:
            return 0.0
        active_start = max(self._l10n_ar_get_seniority_date() or semester_start, semester_start)
        active_end = min(self.date_to or semester_end, semester_end)
        if active_start > active_end:
            return 0.0
        total_days = (semester_end - semester_start).days + 1
        active_days = (active_end - active_start).days + 1
        return active_days / total_days

    def _l10n_ar_compute_sac_amount(self, base_amount=False):
        self.ensure_one()
        base_amount = base_amount or self._l10n_ar_get_sac_base()
        divisor = self._rule_parameter("l10n_ar_sac_divisor") or 2.0
        return (base_amount / divisor) * self._l10n_ar_get_sac_proportional_ratio() if divisor else 0.0

    def _l10n_ar_get_payment_account(self):
        self.ensure_one()
        allocations = self.compute_salary_allocations()
        if allocations:
            first_bank_id = next(iter(allocations))
            if first_bank_id:
                return self.env["res.partner.bank"].browse(int(first_bank_id))
        return (
            self.employee_id.bank_account_ids.filtered("allow_out_payment")[:1]
            or self.employee_id.bank_account_ids[:1]
        )

    def _l10n_ar_get_net_amount_text(self):
        self.ensure_one()
        amount = abs(self.net_wage or 0.0)
        return self.currency_id.with_context(lang=self.employee_id.lang or self.env.lang).amount_to_text(amount)
