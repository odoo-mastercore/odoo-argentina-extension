##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models
from odoo.exceptions import UserError, ValidationError


class StockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    # TODO: Esperar merge de parte de Adhoc para eliminar esto
    def process(self):
        pickings_to_do = self.env['stock.picking']
        pickings_not_to_do = self.env['stock.picking']
        for line in self.immediate_transfer_line_ids:
            if line.to_immediate is True:
                pickings_to_do |= line.picking_id
            else:
                pickings_not_to_do |= line.picking_id

        for picking in pickings_to_do:
            # If still in draft => confirm and assign
            if picking.state == 'draft':
                picking.action_confirm()
                if picking.state != 'assigned':
                    picking.action_assign()
                    if picking.state != 'assigned':
                        raise UserError(_("Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
            picking.move_ids._set_quantities_to_reservation()

        pickings_to_validate = self.env.context.get('button_validate_picking_ids')
        res = False
        if pickings_to_validate:
            pickings_to_validate = self.env['stock.picking'].browse(pickings_to_validate)
            pickings_to_validate = pickings_to_validate - pickings_not_to_do
            res = pickings_to_validate.with_context(skip_immediate=True).button_validate()
        else:
            res = True

        pickings = self.env['stock.picking'].browse(
            self._context.get('picking_ids')).filtered(lambda p: p.book_required and p.voucher_ids)
        if pickings:
            return {
                'acions': [
                    res,
                    pickings.do_print_voucher(),
                ],
                'type': 'ir.actions.act_multi',
            }
        else:
            return res