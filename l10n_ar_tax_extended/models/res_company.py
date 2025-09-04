# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0) 
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
###############################################################################
from odoo import fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    enabled_retention_currency = fields.Boolean(string='Permitir Retenciones en Divisas')
           