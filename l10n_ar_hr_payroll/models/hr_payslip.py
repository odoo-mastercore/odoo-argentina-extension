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
from odoo.tools.misc import format_date


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    l10n_ar_payment_method = fields.Selection(
        selection=[
            ("bank_transfer", "Transferencia bancaria"),
            ("cash", "Efectivo"),
            ("check", "Cheque"),
            ("other", "Otro"),
        ],
        string="Payment Method",
        default="bank_transfer",
    )
    l10n_ar_payment_method_note = fields.Char(string="Payment Method Detail")

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

    def _l10n_ar_get_employee_entry_date(self):
        self.ensure_one()
        versions = self.employee_id.with_context(active_test=False).version_ids
        contract_dates = [d for d in versions.mapped("contract_date_start") if d]
        if contract_dates:
            return min(contract_dates)
        effective_dates = [d for d in versions.mapped("date_start") if d]
        return min(effective_dates) if effective_dates else (self.version_id.contract_date_start or self.version_id.date_start)

    def _l10n_ar_get_payment_place(self):
        self.ensure_one()
        return self.company_id.partner_id.city or self.company_id.partner_id.state_id.name or "-"

    def _l10n_ar_get_payment_date(self):
        self.ensure_one()
        return self.paid_date or self.compute_date or fields.Date.today()

    def _l10n_ar_get_employee_entry_date_display(self):
        self.ensure_one()
        entry_date = self._l10n_ar_get_employee_entry_date()
        return format_date(self.env, entry_date) if entry_date else "-"

    def _l10n_ar_get_payment_date_display(self):
        self.ensure_one()
        payment_date = self._l10n_ar_get_payment_date()
        return format_date(self.env, payment_date) if payment_date else "-"

    def _l10n_ar_get_payment_method_display(self):
        self.ensure_one()
        if self.l10n_ar_payment_method == "other":
            return self.l10n_ar_payment_method_note or "Otro"
        if self.l10n_ar_payment_method:
            return dict(self._fields["l10n_ar_payment_method"].selection).get(self.l10n_ar_payment_method)
        return "Transferencia bancaria" if self._l10n_ar_get_payment_account() else "-"

    def _l10n_ar_get_legajo(self):
        self.ensure_one()
        return self.employee_id.registration_number or str(self.employee_id.id)

    def _l10n_ar_get_deduction_rate(self, line):
        self.ensure_one()
        if line.code == "AR_JUB":
            return self._rule_parameter("l10n_ar_employee_jubilacion_rate")
        if line.code == "AR_LEY19032":
            return self._rule_parameter("l10n_ar_employee_ley_19032_rate")
        if line.code == "AR_OBRA_SOC":
            return self._rule_parameter("l10n_ar_employee_obra_social_rate")
        if line.code == "AR_SINDICATO":
            return self.version_id.l10n_ar_union_rate
        return line.rate
