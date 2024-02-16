# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields
from datetime import datetime, timedelta
from odoo.tools.misc import format_date
from odoo.exceptions import UserError, ValidationError


class ResCurrency(models.Model):
    _inherit = "res.currency"
    
    code = fields.Char(string='Código de la moneda')