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


class l10nArPaymentWithholding(models.Model):
    _inherit = "l10n_ar.payment.withholding"

    foreign_currency_id = fields.Many2one(
        "res.currency",
        string="Foreign currency",
        related="payment_id.counterpart_currency_id"
    )
    amount_currency = fields.Float(string="Importe en Divisa")

    @api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        if self.foreign_currency_id and self.amount_currency:
            rate = self.env["res.currency"]._get_conversion_rate(
                from_currency=self.foreign_currency_id,
                to_currency=self.company_id.currency_id,
                company=self.company_id,
                date=self.payment_id.date,
            ) or 1
            self.amount = rate * self.amount_currency