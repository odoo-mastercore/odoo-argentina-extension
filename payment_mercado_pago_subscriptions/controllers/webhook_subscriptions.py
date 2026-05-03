# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
##############################################################################
"""Controller del webhook de Suscripciones Mercado Pago.

Recibe POSTs firmados de MP con los topics:

- ``subscription_preapproval``
- ``subscription_authorized_payment``
- ``payment``
- ``subscription_preapproval_plan``

Para cada notificación:

1. Valida el header ``x-signature`` con HMAC-SHA256 contra
   ``payment.provider.mp_webhook_secret``.
2. Lee el ``data.id`` del payload y consulta el endpoint ``GET``
   correspondiente para hidratar el recurso (canon: nunca confiar en el
   payload del webhook, siempre re-leer).
3. Aplica los cambios en el modelo Odoo correspondiente
   (``mp.preapproval``, ``mp.authorized.payment``,
   ``mp.preapproval.plan``).
4. Devuelve HTTP 200 dentro de los 22 segundos para evitar reintentos.

La idempotencia se garantiza a nivel del payload ID y los SQL
constraints (``mp_id`` unique en cada modelo). Si MP reenvía la misma
notificación, las escrituras son no-op.
"""

import json
import logging

from odoo import http
from odoo.http import request

from ..services import mp_signature
from .. import const

_logger = logging.getLogger(__name__)


class MPSubscriptionsWebhookController(http.Controller):

    @http.route(
        const.SUBSCRIPTIONS_WEBHOOK_ROUTE,
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def webhook(self, **post):
        """Endpoint público del webhook MP Suscripciones.

        Responde 200 lo más rápido posible. Cualquier error procesando
        el evento se loguea pero no se propaga al request, para no
        gatillar reintentos infinitos del lado MP. La consistencia se
        recupera en el siguiente ``GET`` o en el cron de sincronización.
        """
        raw_body = request.httprequest.get_data() or b''
        try:
            payload = json.loads(raw_body.decode('utf-8') or '{}')
        except (ValueError, UnicodeDecodeError):
            _logger.warning("MP webhook: invalid JSON body, ignoring.")
            return request.make_json_response({'received': False, 'reason': 'invalid_json'})

        topic = payload.get('type') or payload.get('topic')
        data = payload.get('data') or {}
        data_id = str(data.get('id') or '')
        action = payload.get('action') or ''

        if not topic or not data_id:
            _logger.warning(
                "MP webhook: missing topic or data.id (topic=%s, data_id=%s).",
                topic, data_id,
            )
            return request.make_json_response({'received': False, 'reason': 'missing_fields'})

        if topic not in const.WEBHOOK_TOPICS_HANDLED:
            _logger.info("MP webhook: unhandled topic %s, skipping.", topic)
            return request.make_json_response({'received': True, 'handled': False})

        provider = self._find_provider_for_webhook()
        if not provider:
            _logger.error("MP webhook: no provider with mp_webhook_secret configured.")
            return request.make_json_response({'received': False, 'reason': 'no_provider'})

        # Validar firma.
        signature_header = request.httprequest.headers.get(const.HEADER_WEBHOOK_SIGNATURE, '')
        request_id = request.httprequest.headers.get(const.HEADER_WEBHOOK_REQUEST_ID, '')
        try:
            valid = mp_signature.verify_signature(
                secret=provider.sudo().mp_webhook_secret,
                data_id=data_id,
                signature_header=signature_header,
                request_id=request_id,
            )
        except mp_signature.MPSignatureError as exc:
            _logger.error("MP webhook: signature validation error: %s", exc)
            return request.make_json_response({'received': False, 'reason': 'signature_error'})
        if not valid:
            _logger.warning(
                "MP webhook: invalid signature for data_id=%s, topic=%s.",
                data_id, topic,
            )
            return request.make_json_response({'received': False, 'reason': 'invalid_signature'})

        # Despachar al handler correspondiente.
        try:
            self._dispatch(provider, topic, data_id, action, payload)
        except Exception as exc:  # noqa: BLE001
            _logger.exception(
                "MP webhook: error processing topic=%s data_id=%s: %s",
                topic, data_id, exc,
            )
            # Igualmente devolvemos 200: el cron de sincronización va a
            # reconciliar después. Reintentar al infinito no agrega valor.
            return request.make_json_response({'received': True, 'handled': False})

        return request.make_json_response({'received': True, 'handled': True})

    # ------------------------------------------------------------------ #
    #  Internals                                                         #
    # ------------------------------------------------------------------ #

    def _find_provider_for_webhook(self):
        """Devuelve el primer provider MP con webhook_secret cargado.

        En instalaciones multi-company puede haber varios providers; este
        controlador asume que hay uno solo activo con secret. Si en el
        futuro hay multi-tenancy de webhooks, agregar discriminador por
        URL o subpath.
        """
        return request.env['payment.provider'].sudo().search([
            ('code', '=', 'mercado_pago'),
            ('mp_webhook_secret', '!=', False),
            ('mp_use_direct_api', '=', True),
            ('state', 'in', ('enabled', 'test')),
        ], limit=1)

    def _dispatch(self, provider, topic, data_id, action, payload):
        env = request.env(su=True)
        client = provider._mp_get_client()

        if topic == const.WEBHOOK_TOPIC_PREAPPROVAL:
            self._handle_preapproval(env, client, data_id, action)
        elif topic == const.WEBHOOK_TOPIC_AUTHORIZED_PAYMENT:
            self._handle_authorized_payment(env, client, data_id, action)
        elif topic == const.WEBHOOK_TOPIC_PAYMENT:
            self._handle_payment(env, client, data_id, action)
        elif topic == const.WEBHOOK_TOPIC_PREAPPROVAL_PLAN:
            self._handle_preapproval_plan(env, client, data_id, action)

    def _handle_preapproval(self, env, client, data_id, action):
        """Sincroniza ``mp.preapproval`` desde GET /preapproval/{id}."""
        preapproval = env['mp.preapproval'].search([('mp_id', '=', data_id)], limit=1)
        if not preapproval:
            _logger.info(
                "MP webhook: preapproval %s not found locally; skipping (probable foreign suscriber).",
                data_id,
            )
            return
        response = client.get_preapproval(data_id)
        preapproval._apply_mp_payload(response)
        _logger.info(
            "MP webhook: preapproval %s synced, status=%s, action=%s.",
            data_id, response.get('status'), action,
        )

    def _handle_authorized_payment(self, env, client, data_id, action):
        """Sincroniza/crea ``mp.authorized.payment`` y dispara hook de
        consumidores cuando la cuota cierra exitosa.
        """
        response = client.get_authorized_payment(data_id)
        preapproval_mp_id = response.get('preapproval_id')
        if not preapproval_mp_id:
            _logger.warning("MP webhook: authorized_payment %s without preapproval_id.", data_id)
            return
        preapproval = env['mp.preapproval'].search(
            [('mp_id', '=', str(preapproval_mp_id))], limit=1
        )
        if not preapproval:
            _logger.info(
                "MP webhook: parent preapproval %s not found locally; skipping authorized_payment %s.",
                preapproval_mp_id, data_id,
            )
            return
        record = env['mp.authorized.payment'].search([('mp_id', '=', data_id)], limit=1)
        if not record:
            record = env['mp.authorized.payment'].create({
                'preapproval_id': preapproval.id,
                'mp_id': data_id,
            })
        record._apply_mp_payload(response)
        _logger.info(
            "MP webhook: authorized_payment %s synced, status=%s, payment_status=%s.",
            data_id, record.status, record.payment_status,
        )
        # Disparar hook si la cuota cerró exitosa. Los módulos
        # consumidores (tupymeclara_subscription, etc.) heredan
        # _on_processed_approved para implementar la lógica
        # post-cobro (facturación, activación de funcionalidad).
        if (record.status == const.AUTHORIZED_PAYMENT_STATUS_PROCESSED
                and record.payment_status == 'approved'):
            try:
                record._on_processed_approved()
            except Exception:  # noqa: BLE001
                _logger.exception(
                    "MP webhook: error in _on_processed_approved for cuota %s; "
                    "the cuota state was already persisted, retry can come from "
                    "the sync cron or a manual re-dispatch.",
                    data_id,
                )

    def _handle_payment(self, env, client, data_id, action):
        """Hidrata payment real (``/v1/payments/{id}``) y, si está vinculado
        a una cuota recurrente, sincroniza el ``payment_status`` en la cuota.
        """
        response = client.get_payment(data_id)
        # Buscar la cuota a la que pertenece (por payment.metadata o
        # external_reference). La asociación robusta se hace cuando el
        # webhook subscription_authorized_payment trae el payment.id en
        # su payload — acá sólo registramos el evento por si hace falta
        # consultarlo después.
        ext_ref = response.get('external_reference')
        cuota = env['mp.authorized.payment'].search(
            [('payment_id_mp', '=', data_id)], limit=1,
        )
        if not cuota and ext_ref:
            preapproval = env['mp.preapproval'].search(
                [('external_reference', '=', ext_ref)], limit=1
            )
            if preapproval:
                _logger.info(
                    "MP webhook: payment %s linked by external_reference to preapproval %s.",
                    data_id, preapproval.mp_id,
                )
        if cuota:
            cuota.write({
                'payment_id_mp': data_id,
                'payment_status': response.get('status'),
            })
        _logger.info(
            "MP webhook: payment %s status=%s, ext_ref=%s.",
            data_id, response.get('status'), ext_ref,
        )

    def _handle_preapproval_plan(self, env, client, data_id, action):
        """Sincroniza ``mp.preapproval.plan`` desde GET /preapproval_plan/{id}."""
        plan = env['mp.preapproval.plan'].search([('mp_id', '=', data_id)], limit=1)
        if not plan:
            _logger.info(
                "MP webhook: plan %s not found locally; skipping (foreign).",
                data_id,
            )
            return
        response = client.get_preapproval_plan(data_id)
        plan.write({
            'state': 'active' if response.get('status') == 'active' else 'inactive',
            'init_point': response.get('init_point') or plan.init_point,
        })
