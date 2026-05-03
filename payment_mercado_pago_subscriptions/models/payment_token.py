# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
##############################################################################

from odoo import fields, models


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    mp_card_id = fields.Char(
        string='MP Card ID',
        readonly=True,
        index=True,
        help='Identificador persistente de la tarjeta en Mercado Pago. A '
             'diferencia del card_token (efímero), el card_id sobrevive a '
             'rotaciones por reemisión de la tarjeta cuando MP aplica '
             'account updater. Se usa para reasignar la tarjeta a un '
             'preapproval sin perder la suscripción.',
    )
