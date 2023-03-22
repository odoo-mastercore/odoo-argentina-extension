from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.date_utils import get_timedelta
import logging

_logger = logging.getLogger(__name__)


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    def process(self):
        super().process()
        pickings = self.env['stock.picking'].browse(
            # if we came, for eg, from a sale order, active_id would be the
            # sale order id
            # self._context.get('active_id'))
            # TODO we should also fix odoo methods
            self._context.get('picking_ids')).filtered('book_required')
        if pickings:
            return {
                'actions': [
                    {'type': 'ir.actions.act_window_close'},
                    pickings.do_print_voucher(),
                ],
                'type': 'ir.actions.act_multi',
            }


