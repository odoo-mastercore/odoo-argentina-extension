# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields
from datetime import datetime, timedelta
from odoo.tools.misc import format_date
from odoo.exceptions import UserError, ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    currency_code = fields.Char(string='Código de la moneda', compute="_compute_currency_code")

    @api.depends('currency_id')
    def _compute_currency_code(self):
        for aml in self:
            aml.currency_code = (aml.currency_id.code if (len(aml.currency_id) > 0) else self.env.company.currency_id.code)
