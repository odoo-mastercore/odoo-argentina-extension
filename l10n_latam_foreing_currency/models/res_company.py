# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, frozendict
import logging
_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = "res.company"

    foreign_currency_id = fields.Many2one('res.currency',
        string='Divisa', default=lambda x: x.env.ref('base.USD')
    )
