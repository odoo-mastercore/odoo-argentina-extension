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
    
    company_foreign_currency_id = fields.Many2one(string='Foreign Company Currency', readonly=True,
        related='company_id.foreign_currency_id')
    amount_total_signed_foreign = fields.Monetary(string='Importe Moneda Extranjera', currency_field='company_foreign_currency_id')
    amount_residual_foreign = fields.Monetary(string='Importe Adeudado Moneda Extranjera', currency_field='company_foreign_currency_id')
    amount_untaxed_signed_foreign = fields.Monetary(string='Impuestos no incluidos en Moneda Extranjera', currency_field='company_foreign_currency_id')

    def _select(self):
        return super(AccountInvoiceReport, self)._select() + ", move.amount_untaxed_signed_foreign as amount_untaxed_signed_foreign, \
        move.amount_total_signed_foreign as amount_total_signed_foreign, move.amount_residual_foreign as amount_residual_foreign"
