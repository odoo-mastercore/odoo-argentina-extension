# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
##############################################################################

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    mp_authorized_payment_id = fields.Many2one(
        'mp.authorized.payment',
        string='Cuota MP de origen',
        copy=False,
        index=True,
        readonly=True,
        help='Cuota recurrente de Mercado Pago (authorized_payment) que '
             'originó esta factura. Sólo se setea cuando la factura fue '
             'generada automáticamente por el handler de webhook al '
             'recibir processed=approved.',
    )
