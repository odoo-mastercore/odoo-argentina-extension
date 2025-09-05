# -*- coding: utf-8 -*-
################################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
################################################################################
from odoo import api, models, fields, _
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.constrains("currency_id", "company_id", "l10n_ar_withholding_line_ids")
    def _check_withholdings_and_currency(self):
        for rec in self:
            if not rec.company_id.enabled_retention_currency:
                return super()._check_withholdings_and_currency()
            pass

    def _prepare_witholding_write_off_vals(self):
        res = super()._prepare_witholding_write_off_vals()
        for line in self.l10n_ar_withholding_line_ids:
            if line.amount_currency and line.foreign_currency_id and res:
                res[0].update({
                    'currency_id': line.foreign_currency_id.id,
                    'amount_currency': line.amount_currency
                })
        return res