# -*- coding: utf-8 -*-
###############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################

from odoo import models, fields
from odoo.exceptions import UserError, ValidationError


class RemitoWizard(models.TransientModel):
    _name = 'remito.wizard'

    has_number = fields.Boolean('Has Number')
    sale_order_id = fields.Many2one('sale.order', string='Orden')
    remito_number = fields.Char('Remito Number', related='sale_order_id.remito_number')
    next_voucher_number = fields.Integer(
        'Next Voucher Number',
        related='book_id.sequence_id.number_next_actual',
    )
    book_id = fields.Many2one(
        'stock.book',
        'Book',
        related='sale_order_id.book_id'
    )

    def clean(self):
        self.sale_order_id.write({
            'remito_number': ''
        })
        # self.sale_order_id.remito_number = False
        return {"type": "ir.actions.act_window_close"}

    def print(self):
        self.env.ref('l10n_ar_remito_sale_order.action_report_remito').report_action(self.sale_order_id)
        return {"type": "ir.actions.act_window_close"}

    def assign(self):
        self.sale_order_id.remito_number = self.book_id.sequence_id.next_by_id()
        self.env.ref('l10n_ar_remito_sale_order.action_report_remito').report_action(self.sale_order_id)
        return {"type": "ir.actions.act_window_close"}