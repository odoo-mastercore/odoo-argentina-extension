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

    counterpart_currency_amount_aux = fields.Float(string="Importe en moneda")

    @api.depends("counterpart_currency_id", "company_id", "date", "counterpart_currency_amount_aux")
    def _compute_counterpart_exchange_rate(self):
        for rec in self:
            if rec.counterpart_currency_id and not rec.counterpart_currency_amount_aux:
                rate = self.env["res.currency"]._get_conversion_rate(
                    from_currency=rec.company_currency_id,
                    to_currency=rec.counterpart_currency_id,
                    company=rec.company_id,
                    date=rec.date,
                )
                rec.counterpart_exchange_rate = 1 / rate if rate else False
            elif rec.counterpart_currency_id and rec.counterpart_currency_amount_aux:
                rate = 1 / (rec.counterpart_currency_amount_aux / rec.amount)
                rec.counterpart_exchange_rate = rate or False
            elif not rec.counterpart_currency_id:
                rec.counterpart_exchange_rate = False