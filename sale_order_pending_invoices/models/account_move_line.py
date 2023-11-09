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
    open_invoice_count = fields.Integer(string="Invoice Count", compute='_get_pending_invoiced')
    open_invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string="Open Invoices",
        compute='_get_pending_invoiced',
        copy=False)
    
    @api.depends('order_line.invoice_lines')
    def _get_pending_invoiced(self):
        for order in self:
            invoices = order.env['account.move'].search([('partner_id','=',order.partner_id.id)])
            open_invoices = invoices.filtered(lambda r: r.move_type in 
                                        ('out_invoice', 'out_refund') and r.payment_state in ('not_paid','partial'))
            _logger.warning('open_invoices %s', open_invoices)
            pending_invoices = invoices.filtered(lambda r: r.move_type in 
                                        ('out_invoice', 'out_refund') and 
                                        r.payment_state in ('not_paid','partial') and fields.Date.today() >= r.invoice_date_due)
            _logger.warning('pending_invoices %s', pending_invoices)
            order.pending_invoice_ids = pending_invoices
            order.pending_invoice_count = len(pending_invoices)
            order.open_invoice_ids = open_invoices
            order.open_invoice_count = len(open_invoices)

    def action_view_pending_invoice(self):
        pending_invoice = self.mapped('pending_invoice_ids')
        action = self.env['ir.actions.actions']._for_xml_id('sale_order_pending_invoices.action_pending_invoice')
        if len(pending_invoice) >= 1:
            action['domain'] = [('id', 'in', pending_invoice.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        action['context'] = context
        return action      

    def action_view_open_invoice(self):
        open_invoice = self.mapped('open_invoice_ids')
        action = self.env['ir.actions.actions']._for_xml_id('sale_order_pending_invoices.action_open_invoice')
        if len(open_invoice) >= 1:
            action['domain'] = [('id', 'in', open_invoice.ids)]
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        action['context'] = context
        return action      