# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
#
##############################################################################
from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestAccountPaymentState(TransactionCase):

    def test_compute_state_marks_payment_paid_without_posting(self):
        payment = self.env["account.payment"].new({"state": "in_process"})

        with patch.object(
            payment.__class__,
            "_get_account_ux_payments_to_mark_paid",
            autospec=True,
            return_value=payment,
        ), patch.object(
            payment.__class__,
            "action_post",
            autospec=True,
        ) as action_post:
            payment._compute_state()

        self.assertEqual(payment.state, "paid")
        action_post.assert_not_called()

    def test_compute_state_respects_skip_context(self):
        payment = self.env["account.payment"].new({"state": "in_process"})

        with patch.object(
            payment.__class__,
            "_get_account_ux_payments_to_mark_paid",
            autospec=True,
        ) as payments_to_mark_paid:
            payment.with_context(skip_payment_state_computation=True)._compute_state()

        payments_to_mark_paid.assert_not_called()
