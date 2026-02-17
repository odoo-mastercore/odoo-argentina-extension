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
        string="Seniority Date",
        tracking=True,
        groups="hr_payroll.group_hr_payroll_user",
        help="Reference start date used for seniority-based payroll rules.",
    )
    l10n_ar_seniority_percent = fields.Float(
        string="Seniority Rate (%)",
        default=0.0,
        tracking=True,
        groups="hr_payroll.group_hr_payroll_user",
        help="Additional percentage applied per completed seniority year.",
    )
    l10n_ar_union_rate = fields.Float(
        string="Union Contribution (%)",
        default=0.0,
        tracking=True,
        groups="hr_payroll.group_hr_payroll_user",
        help="Union deduction percentage over taxable salary.",
    )

    @api.constrains("l10n_ar_seniority_percent", "l10n_ar_union_rate")
    def _check_l10n_ar_rates(self):
        for version in self:
            if version.l10n_ar_seniority_percent < 0 or version.l10n_ar_seniority_percent > 100:
                raise ValidationError(_("Seniority rate must be between 0 and 100."))
            if version.l10n_ar_union_rate < 0 or version.l10n_ar_union_rate > 100:
                raise ValidationError(_("Union contribution rate must be between 0 and 100."))

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

