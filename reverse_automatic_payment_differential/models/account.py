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


class AccountMoveLines(models.Model):
    _inherit = "account.move.line"

    def _get_reconcile_lines(self):
        return self._all_reconciled_lines().filtered(
            lambda l: l.matched_debit_ids or l.matched_credit_ids)