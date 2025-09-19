# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2024-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
from odoo import models, fields, api, _
from datetime import date, datetime
from pytz import timezone
import logging
_logger = logging.getLogger(__name__)


class resCurrency(models.Model):
    _inherit = 'res.currency'

    enabled_button_navbar = fields.Boolean(
        string='Enable Currency Rate Button in Navbar',
        default=False
    )

    def currency_rate_navbar(self):
        currencies = self.search([
            ('active', '=', True),
            ('is_company_currency', '=', False),
            ('enabled_button_navbar', '=', True)
        ])
        currency_list = [{
            'id': currency.id,
            'name': currency.name,
            'symbol': currency.symbol,
            'rate': round(1 / currency.rate, 4),
        } for currency in currencies]
        return currency_list