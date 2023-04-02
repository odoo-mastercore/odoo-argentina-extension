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
        journal_id = self.env['account.journal'].search([
            ('differential_reverse', '=', True)
        ], limit=1)
        if journal_id:
            move_line = self.env['account.move.line'].search([
                ('journal_id', '=', journal_id.id),
                ('move_id.state', '=', 'posted'),
                ('company_id', '=', self.company_id.id),
                ('partner_id', '=', self.partner_id.id),
                ('move_id.reversed_entry_id', '=', False)
            ])
            if move_line:
                line_to_reverse = False
                for line in move_line:
                    reconciled_lines = line._get_reconcile_lines()
                    for r_line in reconciled_lines:
                        if r_line.move_id.payment_group_id.id == self.id:
                            self._reverse_automatic_move(line.move_id)
        return res

    def _reverse_automatic_move(self, move_id):
        moves = move_id
        refund_method = 'modify'
        date_mode = 'custom'

        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))
        batches = [
            [self.env['account.move'], [], True],   # Moves to be cancelled by the reverses.
            [self.env['account.move'], [], False],  # Others.
        ]
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = default_vals.get('auto_post') != 'no'
            is_cancel_needed = not is_auto_post and refund_method in ('cancel', 'modify')
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)

        # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for moves, default_values_list, is_cancel_needed in batches:
            new_moves = moves._reverse_moves(default_values_list, cancel=is_cancel_needed)

            if refund_method == 'modify':
                moves_vals_list = []
                for move in moves.with_context(include_business_fields=True):
                    moves_vals_list.append(move.copy_data({'date': fields.Date.context_today(self) if date_mode == 'custom' else move.date})[0])
                new_moves = self.env['account.move'].create(moves_vals_list)

            moves_to_redirect |= new_moves

        # self.new_move_ids = moves_to_redirect

    def _prepare_default_reversal(self, move):
        reverse_date = move.date
        return {
            'ref': _('Reversal of: %s', move.name),
            'date': reverse_date,
            'invoice_date_due': reverse_date,
            'invoice_date': move.is_invoice(include_receipts=True) and (move.date) or False,
            'journal_id': move.journal_id.id,
            'invoice_payment_term_id': None,
            'invoice_user_id': move.invoice_user_id.id,
            'auto_post': 'at_date' if reverse_date > fields.Date.context_today(self) else 'no',
        }
