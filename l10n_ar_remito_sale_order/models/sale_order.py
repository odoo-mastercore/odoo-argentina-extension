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

    book_id = fields.Many2one(
        'stock.book',
        'Voucher Book',
        copy=False,
        ondelete='restrict',
    )
    remito_number = fields.Integer('Número de remito', default=False)
    driver_id = fields.Many2one('res.partner', 
                                string='Transportista', 
                                domain="[('is_driver','=', True)]")
    

    def open_pickup(self):
        rec = super(saleOrder, self).open_pickup()
        self.write({
            'book_id': self.env.ref('l10n_ar_remito_sale_order.stock_book_1')
        })
        return rec

    def generate_remito(self):
        if not self.book_id:
            raise ValidationError(_('No se ha seleccionado un libro'))
        if not self.driver_id:
            raise ValidationError(_('No se ha seleccionado un transportista'))
        if not self.remito_number:
            company = self.mapped('company_id')
            self.remito_number = self.env['ir.sequence'].with_company(company).next_by_code('remito.sale.order')
        return self.env.ref('l10n_ar_remito_sale_order.action_report_remito').report_action(self)