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
from odoo.tools import ( float_is_zero )
_logger = logging.getLogger(__name__)


class AccountPaymentGroup(models.Model):
    _inherit = "account.payment.group"

    def post(self):
        res = super(AccountPaymentGroup, self).post()
        reversed_move = False
        if self.apply_foreign_payment:
            amount_payment = sum(self.payment_ids.mapped('amount'))
            amount_to_pay = sum(self.to_pay_move_line_ids.mapped('amount_currency'))
            if float_is_zero(amount_to_pay - amount_payment):
                reversed_move = True
        else:
            reversed_move = True
        journal_id = self.env['account.journal'].search([
            ('differential_reverse', '=', True),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if journal_id and reversed_move:
            all_move_line = self.env['account.move.line'].search([
                ('journal_id', '=', journal_id.id),
                ('move_id.state', '=', 'posted'),
                ('company_id', '=', self.company_id.id),
                ('partner_id', '=', self.partner_id.id),
                ('move_id.reversed_entry_id', '=', False),
            ])
            move_line_unreversed_ids = []
            moves_to_reverse = []
            if all_move_line:
                for line in all_move_line:
                    unreversed_move_line = self.env['account.move.line'].search([
                        ('move_id.reversed_entry_id', '=', line.move_id.id),
                        ('move_id.company_id', '=', line.company_id.id)
                    ])
                    if not unreversed_move_line:
                        move_line_unreversed_ids.append(line.id)
            if move_line_unreversed_ids:
                move_lines = self.env['account.move.line'].browse(move_line_unreversed_ids)
                for line in move_lines:
                    reconciled_lines = line._get_reconcile_lines()
                    if reconciled_lines:
                        for r_line in reconciled_lines:
                            if r_line.move_id.payment_group_id and r_line.move_id.payment_group_id.id == self.id:
                                if line.move_id.id not in moves_to_reverse:
                                    moves_to_reverse.append(line.move_id.id)
            moves = self.env['account.move'].browse(moves_to_reverse)
            if moves:
                self._reverse_automatic_move(moves)
        return res

    def _reverse_automatic_move(self, move_id):
        move_reversal = self.env['account.move.reversal']\
            .with_context(active_model="account.move", active_ids=move_id.ids)\
            .create({
                'company_id': move_id[0].company_id.id,
                'journal_id': move_id[0].journal_id.id,
                'reason': "(Automático)",
                'refund_method': 'cancel',
            })
        move_reversal.reverse_moves()
