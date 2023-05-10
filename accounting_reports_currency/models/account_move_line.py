# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    amount_currency_company = fields.Float(compute='_compute_amount_currency_company', 
                                           string='Monto en moneda de la compañia', 
                                           store=True)
    
    @api.depends('amount_currency', 'currency_id')
    def _compute_amount_currency_company(self):
        for rec in self:
            if rec.currency_id.id != rec.company_id.currency_id:
                rate = self.env['res.currency.rate'].search([
                    ('currency_id', '=', rec.currency_id.id),
                    ('name', '<=', rec.date)
                    ],limit=1)
                rec.amount_currency_company = rec.amount_currency / rate.company_rate
            else:
                rec.amount_currency_company = rec.amount_currency
