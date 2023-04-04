# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_draft(self):
        # account
        self.move_id.button_draft()

        # hr_expense
        if 'expense_sheet_id' in self.env['account.move.line']._fields:
            if self.reconciled_bill_ids.expense_sheet_id:
                self.reconciled_bill_ids.expense_sheet_id.write({'state': 'post'})

        # Adhoc account-payment with improvements
        withholdings = self.filtered(lambda x: x.tax_withholding_id)
        for withholding in withholdings:
            liquidity_lines, counterpart_lines, writeoff_lines = withholding._seek_for_lines()
            liquidity_lines._write({
                'tax_repartition_line_id': None,
                'tax_line_id': None,
            })