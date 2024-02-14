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

    def _get_to_pay_move_lines_domain(self):
        rec = super(AccountPaymentGroup, self)._get_to_pay_move_lines_domain()
        rec.append(('move_type','in',['out_invoice','out_refund']))
        return rec