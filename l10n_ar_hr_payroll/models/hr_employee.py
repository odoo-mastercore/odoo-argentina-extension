# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
# See https://www.gnu.org/licenses/agpl-3.0.html
#
##############################################################################

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_ar_cuil = fields.Char(
        "CUIL",
        copy=False,
        tracking=True,
        help="CUIL del trabajador con formato XX-XXXXXXXX-X.",
    )
    l10n_ar_seniority_date = fields.Date(
        readonly=False,
        related="version_id.l10n_ar_seniority_date",
        inherited=True,
        groups="hr_payroll.group_hr_payroll_user",
    )
    l10n_ar_seniority_percent = fields.Float(
        readonly=False,
        related="version_id.l10n_ar_seniority_percent",
        inherited=True,
        groups="hr_payroll.group_hr_payroll_user",
    )
    l10n_ar_union_rate = fields.Float(
        readonly=False,
        related="version_id.l10n_ar_union_rate",
        inherited=True,
        groups="hr_payroll.group_hr_payroll_user",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "l10n_ar_cuil" in vals:
                vals["l10n_ar_cuil"] = self._l10n_ar_normalize_cuil(vals.get("l10n_ar_cuil"))
        return super().create(vals_list)

    def write(self, vals):
        if "l10n_ar_cuil" in vals:
            vals = dict(vals)
            vals["l10n_ar_cuil"] = self._l10n_ar_normalize_cuil(vals.get("l10n_ar_cuil"))
        return super().write(vals)

    def _l10n_ar_normalize_cuil(self, cuil):
        if not cuil:
            return False
        digits = "".join(c for c in cuil if c.isdigit())
        if len(digits) != 11:
            raise ValidationError(_("El CUIL debe contener 11 dígitos (ejemplo: 27-12345678-3)."))
        if not self._l10n_ar_is_valid_cuil_digits(digits):
            raise ValidationError(_("El dígito verificador del CUIL no es válido."))
        return f"{digits[:2]}-{digits[2:10]}-{digits[10]}"

    def _l10n_ar_is_valid_cuil_digits(self, digits):
        weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        total = sum(int(digit) * weight for digit, weight in zip(digits[:10], weights))
        check = 11 - (total % 11)
        if check == 11:
            check = 0
        elif check == 10:
            check = 9
        return int(digits[10]) == check

    def action_open_l10n_ar_cost_simulator(self):
        self.ensure_one()
        if self.company_country_code != "AR":
            raise UserError(_("El simulador está disponible solo para compañías de Argentina."))
        action = self.env["ir.actions.actions"]._for_xml_id(
            "l10n_ar_hr_payroll.action_l10n_ar_cost_simulator_wizard"
        )
        action["context"] = dict(
            self.env.context,
            default_mode="salary_increase",
            default_employee_id=self.id,
            default_company_id=self.company_id.id,
        )
        return action
