# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
##############################################################################

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mp_index_days_before = fields.Integer(
        string='MP — Días antes del cobro para indexar',
        config_parameter='payment_mercado_pago_subscriptions.index_days_before',
        default=1,
        help='Cantidad de días de anticipación al next_payment_date para '
             'que el cron de indexación recalcule y haga PUT al monto del '
             'preapproval. Default 1 día (T-1) — da margen para que MP '
             'procese el cambio y notifique al cliente antes del cobro.',
    )
    mp_index_threshold_percent = fields.Float(
        string='MP — Umbral de cambio para indexar (%)',
        config_parameter='payment_mercado_pago_subscriptions.index_threshold_percent',
        default=1.0,
        help='Delta porcentual mínimo entre el monto actual del preapproval '
             'y el calculado por el hook. Cambios menores a este umbral se '
             'ignoran para evitar ruido al cliente con notificaciones de MP '
             'por movimientos minúsculos. Default 1.0%.',
    )
