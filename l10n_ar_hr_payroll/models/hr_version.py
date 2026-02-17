# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
# See https://www.gnu.org/licenses/agpl-3.0.html
#
##############################################################################

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrVersion(models.Model):
    _inherit = "hr.version"

    l10n_ar_seniority_date = fields.Date(
        string="Fecha de antigüedad",
        tracking=True,
        groups="hr_payroll.group_hr_payroll_user",
        help="Fecha de referencia utilizada para reglas salariales basadas en antigüedad.",
    )
    l10n_ar_seniority_percent = fields.Float(
        string="Porcentaje por antigüedad (%)",
        default=0.0,
        tracking=True,
        groups="hr_payroll.group_hr_payroll_user",
        help="Porcentaje adicional aplicado por cada año completo de antigüedad.",
    )
    l10n_ar_union_rate = fields.Float(
        string="Aporte sindical (%)",
        default=0.0,
        tracking=True,
        groups="hr_payroll.group_hr_payroll_user",
        help="Porcentaje de descuento sindical sobre la remuneración imponible.",
    )

    @api.constrains("l10n_ar_seniority_percent", "l10n_ar_union_rate")
    def _check_l10n_ar_rates(self):
        for version in self:
            if version.l10n_ar_seniority_percent < 0 or version.l10n_ar_seniority_percent > 100:
                raise ValidationError(_("El porcentaje por antigüedad debe estar entre 0 y 100."))
            if version.l10n_ar_union_rate < 0 or version.l10n_ar_union_rate > 100:
                raise ValidationError(_("El aporte sindical debe estar entre 0 y 100."))

    @api.model
    def _get_whitelist_fields_from_template(self):
        whitelisted_fields = super()._get_whitelist_fields_from_template()
        if self.env.company.country_code == "AR":
            whitelisted_fields += [
                "l10n_ar_seniority_date",
                "l10n_ar_seniority_percent",
                "l10n_ar_union_rate",
            ]
        return whitelisted_fields
