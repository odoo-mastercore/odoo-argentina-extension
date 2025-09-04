# -*- coding: utf-8 -*-
################################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
################################################################################
from odoo import api, models, fields, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.constrains("currency_id", "company_id", "l10n_ar_withholding_line_ids")
    def _check_withholdings_and_currency(self):
        for rec in self:
            if not rec.company_id.enabled_retention_currency:
                return super()._check_withholdings_and_currency()
            pass