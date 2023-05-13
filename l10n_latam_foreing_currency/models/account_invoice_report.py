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
    amount_total_foreign = fields.Monetary(string='Total en Divisas',
        currency_field='company_foreign_currency_id'
    )
    amount_residual_foreign = fields.Monetary(string='Adeudado en Divisas',
        currency_field='company_foreign_currency_id'
    )
    amount_untaxed_foreign = fields.Monetary(string='Subtotal en Divisas',
        currency_field='company_foreign_currency_id'
    )
    #Por Ahora funciona porque todas las facturas son en $$ Buscar mejora
    price_subtotal_foreign = fields.Monetary('Precio Subtotal', readonly=True,
        currency_field='invoice_currency_id',
    )

    def _select(self):
        return super(AccountInvoiceReport, self)._select() + """,
        move.amount_untaxed_foreign as amount_untaxed_foreign,
        move.amount_total_foreign as amount_total_foreign,
        move.amount_residual_foreign as amount_residual_foreign,
        line.price_subtotal as price_subtotal_foreign,
        """
