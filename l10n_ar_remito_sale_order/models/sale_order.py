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


class saleOrder(models.Model):
    _inherit = 'sale.order'

    remito_number = fields.Integer('Número de remito')

    def generate_remito(self):
        '''This function prints the voucher'''
        print('333')
        return self.env.ref('l10n_ar_remito_sale_order.action_report_remito').report_action(self)