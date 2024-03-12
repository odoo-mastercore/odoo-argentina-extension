# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2024-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"

    # domain_line_ids = fields.Many2many(
    #     string=_('domain_line_ids'),
    #     comodel_name='account.move.line',
    # )

    def _get_to_pay_move_lines_domain(self):
        rec = super(AccountPaymentGroup, self)._get_to_pay_move_lines_domain()
        rec.append(('move_type','in',['out_invoice','out_refund','in_invoice','in_refund']))
        return rec
    
    # @api.depends('partner_id')
    # def get_domain_payments(self):
    #     for rec in self:
    #         ids = []
    #         if rec.partner_id:
    #             ids = self.env['account.move.line'].search(self._get_to_pay_move_lines_domain()).ids
    #     return ids 