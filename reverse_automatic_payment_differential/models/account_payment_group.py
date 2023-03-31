# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2022-Present.
#
#
###############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"

    def post(self):
        res = super(AccountPaymentGroup, self).post()
        if self.matched_move_line_ids:
            for line in self.matched_move_line_ids:
                if line.move_id.journal_id.differential_reverse:
                    line.move_id.button_cancel()
        return res
