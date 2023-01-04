# -*- coding: utf-8 -*-
###############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################

from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError, UserError
import logging
import requests
import json

_logger = logging.getLogger(__name__)

class SaleSubscriptionTemplateInherit(models.Model):
    _inherit = 'sale.subscription.template'

    recurring_invoicing_type = fields.Selection([
        ('pre_paid', 'Prepago'),
        ('post_paid', 'Postpago')
    ], string='Tipo de factura recurrente')