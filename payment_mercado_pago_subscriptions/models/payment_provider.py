# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
##############################################################################

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services.mp_client import MPClient
from .. import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    mp_use_direct_api = fields.Boolean(
        string='Mercado Pago — Modo directo (sin proxy Odoo)',
        help='Si está activo, las llamadas a la API de Suscripciones MP '
             'salen contra api.mercadopago.com con el access_token propio del '
             'comercio. Si no, el módulo nativo payment_mercado_pago sigue '
             'usando el proxy mercadopago.api.odoo.com para los pagos one-shot.',
    )
    mp_webhook_secret = fields.Char(
        string='Mercado Pago — Webhook secret',
        groups='base.group_system',
        help='Secret HMAC-SHA256 generado en el panel MP → Webhooks. Se usa '
             'para validar la firma del header x-signature en cada '
             'notificación recibida.',
    )

    def _mp_get_client(self):
        """Devuelve un MPClient listo para hablar con MP en modo directo.

        Requiere que el provider esté con mp_use_direct_api=True y tenga
        access_token cargado. Útil tanto para acciones interactivas
        (botones del back) como para crons.
        """
        self.ensure_one()
        if self.code != 'mercado_pago':
            raise UserError(_(
                "Solo el provider Mercado Pago soporta el cliente de "
                "suscripciones."
            ))
        if not self.mp_use_direct_api:
            raise UserError(_(
                "Activá 'Modo directo' en el provider Mercado Pago antes de "
                "usar la API de Suscripciones."
            ))
        if not self.mercado_pago_access_token:
            raise UserError(_(
                "El provider Mercado Pago no tiene access_token cargado."
            ))
        return MPClient(
            access_token=self.mercado_pago_access_token,
            base_url=const.MP_API_BASE_URL,
        )

    def _compute_feature_support_fields(self):
        """Habilita el flag de tokenización para nuestro flow MIT-style.

        El módulo nativo ya marca support_tokenization=True para 'mercado_pago'.
        Mantenemos el comportamiento — solo lo dejamos documentado acá para
        que un dev futuro entienda por qué confiamos en el flag.
        """
        return super()._compute_feature_support_fields()
