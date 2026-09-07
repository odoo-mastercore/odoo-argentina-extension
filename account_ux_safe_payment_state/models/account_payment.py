# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
#
##############################################################################
from odoo import api, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_account_ux_payments_to_mark_paid(self):
        return self.filtered(
            lambda payment: payment.journal_id.type in ("bank", "cash", "credit")
            and payment.state == "in_process"
            and payment.outstanding_account_id
            and len(payment.move_id.line_ids._reconciled_lines()) > 1
            and not payment.payment_method_line_id.payment_account_id.reconcile
        )

    @api.depends("invoice_ids.payment_state", "move_id.line_ids.amount_residual")
    def _compute_state(self):
        skip_state_adjustment = self.env.context.get("skip_payment_state_computation")
        payments = self.with_context(skip_payment_state_computation=True)
        super(AccountPayment, payments)._compute_state()

        if skip_state_adjustment:
            return

        payments._get_account_ux_payments_to_mark_paid().state = "paid"
