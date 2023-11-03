# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2021-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = "sale.order"

    pending_invoice_count = fields.Integer(string="Invoice Count", compute='_get_pending_invoiced')
    pending_invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string="Peding Invoices",
        compute='_get_pending_invoiced',
        copy=False)
    
    @api.depends('order_line.invoice_lines')
    def _get_pending_invoiced(self):
        # The invoice_ids are obtained thanks to the invoice lines of the SO
        # lines, and we also search for possible refunds created directly from
        # existing invoices. This is necessary since such a refund is not
        # directly linked to the SO.
        for order in self:
            invoices = order.env['account.move'].search([('partner_id','=',order.partner_id.id)])
            invoices = invoices.filtered(lambda r: r.move_type in ('out_invoice', 'out_refund') and r.payment_state in ('not_paid','partial'))
            _logger.warning('pending_invoices %s', invoices)
            order.pending_invoice_ids = invoices
            order.pending_invoice_count = len(invoices)

    def action_view_pending_invoice(self):
        invoices = self.mapped('pending_invoice_ids')
        action = self.env['ir.actions.actions']._for_xml_id('sale_order_pending_invoices.action_pending_invoice')
        if len(invoices) >= 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_partner_shipping_id': self.partner_shipping_id.id,
                'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.name,
            })
        action['context'] = context
        return action      