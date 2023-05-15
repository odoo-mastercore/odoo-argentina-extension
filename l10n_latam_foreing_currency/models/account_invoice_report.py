# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2021-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
from odoo import models, fields, api, _

class AccountInvoiceReport(models.Model):

    _inherit = 'account.invoice.report'

    company_foreign_currency_id = fields.Many2one(
        string='Foreign Company Currency', readonly=True,
        related='company_id.foreign_currency_id'
    )
    price_subtotal_foreign = fields.Monetary('Precio Subtotal en Divisa',
        currency_field='company_foreign_currency_id'
    )

    def _select(self):
        return super(AccountInvoiceReport, self)._select() + """,
        line.price_subtotal_foreign as price_subtotal_foreign
        """
