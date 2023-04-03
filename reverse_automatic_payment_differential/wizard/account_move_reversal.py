# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    @api.model
    def default_get(self, fields):
        res = super(AccountMoveReversal, self).default_get(fields)
        # move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.env['account.move']

        # if any(move.state != "posted" for move in move_ids):
        #     raise UserError(_('You can only reverse posted moves.'))
        # if 'company_id' in fields:
        #     res['company_id'] = move_ids.company_id.id or self.env.company.id
        # if 'move_ids' in fields:
        #     res['move_ids'] = [(6, 0, move_ids.ids)]
        # if 'refund_method' in fields:
        #     res['refund_method'] = (len(move_ids) > 1 or move_ids.move_type == 'entry') and 'cancel' or 'refund'
        print("##################### default get")
        print(res)
        return res

    @api.model
    def create(self, vals):
        print("##################### create")
        print(vals)
        return super(AccountMoveReversal, self).create(vals)