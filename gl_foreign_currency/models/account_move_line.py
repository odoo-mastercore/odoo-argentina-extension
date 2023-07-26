# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from odoo import fields, models, tools, api
from odoo.modules.module import get_resource_path

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    aux_inverse_currency_rate = fields.Float('Tasa de cambio para asientos contables', readonly=True, default=0.0)
