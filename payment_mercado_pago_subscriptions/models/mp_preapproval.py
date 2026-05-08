# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
##############################################################################

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .. import const

_logger = logging.getLogger(__name__)


class MPPreapproval(models.Model):
    """Suscripción individual en Mercado Pago (recurso ``preapproval``).

    Cada registro corresponde a una suscripción firmada (o pendiente de
    firma) por un suscriptor. El estado se mantiene sincronizado con MP
    mediante webhooks y consultas explícitas al endpoint
    ``GET /preapproval/{id}``.
    """
    _name = 'mp.preapproval'
    _description = 'Suscripción Mercado Pago (preapproval)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(
        compute='_compute_name',
        store=True,
        help='Nombre legible de la suscripción.',
    )
    provider_id = fields.Many2one(
        'payment.provider',
        string='Proveedor de pago',
        required=True,
        domain="[('code', '=', 'mercado_pago')]",
        ondelete='restrict',
    )
    plan_id = fields.Many2one(
        'mp.preapproval.plan',
        string='Plan asociado',
        ondelete='restrict',
        tracking=True,
        help='Plan MP al que pertenece. Vacío = suscripción "sin plan".',
    )
    mp_id = fields.Char(
        string='MP Preapproval ID',
        copy=False,
        index=True,
        readonly=True,
        tracking=True,
    )
    reason = fields.Char(required=True, tracking=True)
    payer_email = fields.Char(required=True, tracking=True)
    external_reference = fields.Char(copy=False, index=True, tracking=True)

    auto_recurring_frequency = fields.Integer(string='Frecuencia', default=1)
    auto_recurring_frequency_type = fields.Selection(
        [
            (const.FREQUENCY_TYPE_DAYS, 'Días'),
            (const.FREQUENCY_TYPE_MONTHS, 'Meses'),
        ],
        string='Unidad',
        default=const.FREQUENCY_TYPE_MONTHS,
    )
    transaction_amount = fields.Float(
        string='Monto por ciclo',
        required=True,
        digits=(16, 2),
        tracking=True,
    )
    currency_id = fields.Many2one('res.currency', required=True)
    start_date = fields.Datetime(string='Inicio')
    end_date = fields.Datetime(string='Fin')
    back_url = fields.Char(required=True)
    card_token_id_value = fields.Char(
        string='Card Token (efímero)',
        copy=False,
        help='Token de tarjeta generado por el frontend MP. Se usa una vez '
             'al crear el preapproval con status=authorized; después no se '
             'persiste.',
    )

    status = fields.Selection(
        [
            (const.PREAPPROVAL_STATUS_PENDING, 'Pendiente de firma'),
            (const.PREAPPROVAL_STATUS_AUTHORIZED, 'Autorizada'),
            (const.PREAPPROVAL_STATUS_PAUSED, 'Pausada'),
            (const.PREAPPROVAL_STATUS_CANCELLED, 'Cancelada'),
            (const.PREAPPROVAL_STATUS_FINISHED, 'Finalizada'),
        ],
        copy=False,
        tracking=True,
        index=True,
    )
    init_point = fields.Char(string='URL de firma', copy=False, readonly=True)
    payer_id = fields.Char(string='MP Payer ID', readonly=True)
    payer_first_name = fields.Char(string='Nombre del firmante', readonly=True)
    payer_last_name = fields.Char(string='Apellido del firmante', readonly=True)
    mp_card_id = fields.Char(
        string='MP Card ID (persistente)',
        readonly=True,
        help='Identificador de tarjeta en MP que sobrevive a account updater.',
    )
    payment_method_id_mp = fields.Char(string='Medio de pago', readonly=True)

    next_payment_date = fields.Datetime(string='Próximo cobro', readonly=True)
    last_charged_date = fields.Datetime(string='Último cobro exitoso', readonly=True)
    last_charged_amount = fields.Float(string='Último monto cobrado', readonly=True, digits=(16, 2))
    charged_amount_total = fields.Float(string='Total acumulado', readonly=True, digits=(16, 2))
    charged_quantity = fields.Integer(string='Ciclos cobrados', readonly=True)
    pending_charge_quantity = fields.Integer(string='Ciclos pendientes', readonly=True)

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Suscripción Odoo',
        ondelete='set null',
        copy=False,
        index=True,
        help='Orden Odoo (con is_subscription=True) asociada a esta '
             'suscripción MP. Se setea cuando un módulo consumidor llama '
             'sale.order._mp_create_preapproval().',
    )

    authorized_payment_ids = fields.One2many(
        'mp.authorized.payment',
        'preapproval_id',
        string='Cuotas',
    )

    _sql_constraints = [
        ('mp_id_uniq', 'unique(mp_id)', 'El MP Preapproval ID debe ser único.'),
    ]

    @api.depends('reason', 'mp_id', 'payer_email')
    def _compute_name(self):
        for preapproval in self:
            preapproval.name = preapproval.reason or preapproval.mp_id or preapproval.payer_email or _('Nueva suscripción')

    # ------------------------------------------------------------------ #
    #  MP API actions                                                    #
    # ------------------------------------------------------------------ #

    def _build_create_payload(self):
        """Arma el payload para POST /preapproval.

        Reglas observadas en la API de Mercado Pago:

        - Sin ``preapproval_plan_id`` + ``status='pending'`` + sin
          ``card_token_id`` → MP acepta y devuelve ``init_point`` para
          checkout hosted (el suscriptor firma en la UI de MP).
        - Con ``preapproval_plan_id`` + ``status='authorized'`` + con
          ``card_token_id`` → MP acepta. Modo embebido obligatorio.
        - Con ``preapproval_plan_id`` + ``status='pending'`` + sin
          ``card_token_id`` → **MP rechaza** con
          "card_token_id is required". Es decir, asociar a plan
          obliga a flow embebido.

        Cuando el operador no provee ``card_token_id`` (modo hosted),
        omitimos ``preapproval_plan_id`` del payload aunque haya plan
        local seleccionado. Los valores del plan ya están copiados en
        ``auto_recurring`` (vía onchange al seleccionar el plan en el
        form), así que el preapproval queda funcionalmente equivalente.
        El ``plan_id`` local sigue persistido para reporting y
        filtrado en el back de Odoo, pero a nivel MP el preapproval no
        está asociado al ``preapproval_plan``.

        Para preservar la asociación a nivel MP (filtrado en el panel,
        agrupamiento en reportes MP), el flow correcto es **compartir
        el ``init_point`` del plan** al suscriptor en lugar de crear
        un ``mp.preapproval`` desde Odoo. MP se encarga de generar el
        preapproval automáticamente al firmar y enviar webhook.
        """
        self.ensure_one()
        payload = {
            'reason': self.reason,
            'payer_email': self.payer_email,
            'auto_recurring': {
                'frequency': self.auto_recurring_frequency,
                'frequency_type': self.auto_recurring_frequency_type,
                'transaction_amount': self.transaction_amount,
                'currency_id': self.currency_id.name,
            },
            'back_url': self.back_url,
        }
        if self.start_date:
            payload['auto_recurring']['start_date'] = fields.Datetime.to_string(
                self.start_date
            ).replace(' ', 'T') + '.000Z'
        if self.end_date:
            payload['auto_recurring']['end_date'] = fields.Datetime.to_string(
                self.end_date
            ).replace(' ', 'T') + '.000Z'
        if self.external_reference:
            payload['external_reference'] = self.external_reference
        if self.card_token_id_value:
            # Modo embebido: token presente, status authorized desde el
            # alta. Si hay plan, se referencia (MP lo permite junto al
            # token).
            payload['card_token_id'] = self.card_token_id_value
            payload['status'] = const.PREAPPROVAL_STATUS_AUTHORIZED
            if self.plan_id and self.plan_id.mp_id:
                payload['preapproval_plan_id'] = self.plan_id.mp_id
        else:
            # Modo hosted: sin token. NO se incluye preapproval_plan_id
            # porque MP exige token cuando hay plan asociado. El plan
            # local queda solo para reporting interno.
            payload['status'] = const.PREAPPROVAL_STATUS_PENDING
        return payload

    def action_create_in_mp(self):
        """``POST /preapproval`` — crea la suscripción en MP.

        Idempotencia: derivada de ``external_reference`` si existe, o
        UUID generado por el cliente. Tras éxito, persiste ``mp_id``,
        ``status`` e ``init_point``.
        """
        for preapproval in self:
            if preapproval.mp_id:
                raise UserError(_(
                    "La suscripción %s ya tiene MP ID asignado.", preapproval.name
                ))
            client = preapproval.provider_id._mp_get_client()
            payload = preapproval._build_create_payload()
            response = client.create_preapproval(payload)
            preapproval._apply_mp_payload(response)
            preapproval.message_post(body=_(
                "Preapproval creado en MP. ID=%(id)s, status=%(status)s.",
                id=response.get('id'), status=response.get('status'),
            ))
            # Sólo mantenemos el card_token efímero en memoria, no persistido.
            preapproval.card_token_id_value = False
        return True

    def action_sync_from_mp(self):
        """``GET /preapproval/{id}`` — refresca el registro desde MP."""
        for preapproval in self.filtered('mp_id'):
            client = preapproval.provider_id._mp_get_client()
            response = client.get_preapproval(preapproval.mp_id)
            preapproval._apply_mp_payload(response)
        return True

    def action_sync_authorized_payments(self):
        """``GET /authorized_payments/search?preapproval_id={id}`` — trae
        todas las cuotas (recurrencias) desde MP y las persiste o
        actualiza localmente.

        Útil para:

        - Reconciliación cuando el webhook
          ``subscription_authorized_payment`` no llega (URL del webhook
          mal configurada en el panel MP, app sin webhooks, secret
          desactualizado).
        - Recuperación de estado tras incidentes.
        - Auditoría manual desde el back de Odoo.

        Por cada cuota recuperada que esté en estado ``processed`` con
        ``payment_status='approved'``, se dispara el hook
        ``_on_processed_approved``. Como el hook es idempotente
        (chequea ``invoice_id`` antes de generar factura), múltiples
        sincronizaciones no producen duplicados.
        """
        AuthorizedPayment = self.env['mp.authorized.payment']
        for preapproval in self.filtered('mp_id'):
            client = preapproval.provider_id._mp_get_client()
            response = client.search_authorized_payments({
                'preapproval_id': preapproval.mp_id,
            })
            results = response.get('results') or response.get('data') or []
            synced = 0
            for payload in results:
                mp_id = payload.get('id')
                if not mp_id:
                    continue
                mp_id = str(mp_id)
                cuota = AuthorizedPayment.search(
                    [('mp_id', '=', mp_id)], limit=1
                )
                if not cuota:
                    cuota = AuthorizedPayment.create({
                        'preapproval_id': preapproval.id,
                        'mp_id': mp_id,
                    })
                cuota._apply_mp_payload(payload)
                synced += 1
                # Hook post-cobro idempotente: el consumidor decide
                # si genera factura, lo escala al equipo, etc.
                if (cuota.status == const.AUTHORIZED_PAYMENT_STATUS_PROCESSED
                        and cuota.payment_status == 'approved'):
                    cuota._on_processed_approved()
            preapproval.message_post(body=_(
                "Sincronizadas %s cuotas desde MP.", synced
            ))
        return True

    def _mp_update_amount(self, new_amount, idempotency_key=None):
        """``PUT /preapproval/{id}`` con nuevo ``transaction_amount``.

        Pensado para ser invocado desde crons de indexación en módulos
        consumidores. El cambio aplica desde el siguiente cobro (no es
        retroactivo).

        :param float new_amount: nuevo monto en la moneda actual.
        :param str idempotency_key: opcional; si no se pasa, el cliente
            HTTP genera uno.
        """
        for preapproval in self:
            if not preapproval.mp_id:
                raise UserError(_(
                    "No se puede actualizar monto: la suscripción no está sincronizada con MP."
                ))
            client = preapproval.provider_id._mp_get_client()
            payload = {
                'auto_recurring': {
                    'transaction_amount': new_amount,
                    'currency_id': preapproval.currency_id.name,
                },
            }
            response = client.update_preapproval(
                preapproval.mp_id, payload, idempotency_key=idempotency_key
            )
            preapproval._apply_mp_payload(response)
            preapproval.message_post(body=_(
                "Monto actualizado: %(old)s → %(new)s %(cur)s.",
                old=preapproval.transaction_amount,
                new=new_amount,
                cur=preapproval.currency_id.name,
            ))
        return True

    def action_pause(self):
        """``PUT /preapproval/{id}`` con status='paused'."""
        return self._mp_change_status(const.PREAPPROVAL_STATUS_PAUSED)

    def action_resume(self):
        """``PUT /preapproval/{id}`` con status='authorized'."""
        return self._mp_change_status(const.PREAPPROVAL_STATUS_AUTHORIZED)

    def action_cancel(self):
        """``PUT /preapproval/{id}`` con status='cancelled' (terminal)."""
        return self._mp_change_status(const.PREAPPROVAL_STATUS_CANCELLED)

    def _mp_change_status(self, new_status):
        for preapproval in self.filtered('mp_id'):
            client = preapproval.provider_id._mp_get_client()
            response = client.update_preapproval(
                preapproval.mp_id, {'status': new_status}
            )
            preapproval._apply_mp_payload(response)
            preapproval.message_post(body=_(
                "Estado actualizado a %s.", new_status
            ))
        return True

    # ------------------------------------------------------------------ #
    #  Actualización de medio de pago (Card Payment Brick)               #
    # ------------------------------------------------------------------ #

    def _mp_update_card_token(self, card_token_id):
        """``PUT /preapproval/{id}`` con nuevo ``card_token_id``.

        Reemplaza la tarjeta asociada al preapproval por la tokenizada
        en el frontend (Card Payment Brick / CardForm). Cita literal
        de la doc oficial MP:

            "Modificar tarjeta del medio de pago principal | Permite
            modificar la tarjeta asociada a la suscripción existente.
            Envía un PUT con el nuevo token en atributo card_token_id
            para el endpoint /preapproval/{id}."

        Reactivación automática: si el preapproval estaba ``paused``
        (típico tras 4 reintentos fallidos que llevaron la cuenta a
        past_due), incluimos también ``status: authorized`` en el
        mismo PUT para reactivar la suscripción de una vez.

        :param str card_token_id: token efímero (válido 7 días) que
            representa la tarjeta tokenizada client-side. Se obtiene
            del callback ``onSubmit`` del Card Payment Brick.
        :return: dict con la respuesta de MP (preapproval actualizado).
        :raises UserError: si falta ``mp_id`` o ``card_token_id``, o si
            el preapproval está en estado terminal (``cancelled``).
        """
        self.ensure_one()
        if not self.mp_id:
            raise UserError(_(
                "No se puede actualizar la tarjeta: la suscripción no "
                "está sincronizada con Mercado Pago."
            ))
        if not card_token_id:
            raise UserError(_(
                "No se puede actualizar la tarjeta: falta el token "
                "generado por el formulario de pago."
            ))
        if self.status == const.PREAPPROVAL_STATUS_CANCELLED:
            raise UserError(_(
                "La suscripción ya está cancelada y no puede actualizar "
                "su tarjeta. Es necesario crear una suscripción nueva."
            ))

        client = self.provider_id._mp_get_client()
        payload = {'card_token_id': card_token_id}
        # Si el preapproval estaba paused (post past_due), aprovechamos
        # el mismo PUT para reactivarlo. MP acepta ambos cambios en una
        # sola llamada — más limpio y atómico que dos PUTs separados.
        was_paused = self.status == const.PREAPPROVAL_STATUS_PAUSED
        if was_paused:
            payload['status'] = const.PREAPPROVAL_STATUS_AUTHORIZED

        response = client.update_preapproval(self.mp_id, payload)
        self._apply_mp_payload(response)
        if was_paused:
            self.message_post(body=_(
                "Medio de pago actualizado vía Card Payment Brick. "
                "Suscripción reactivada (paused → authorized) en el "
                "mismo PUT."
            ))
        else:
            self.message_post(body=_(
                "Medio de pago actualizado vía Card Payment Brick."
            ))
        return response

    # ------------------------------------------------------------------ #
    #  Indexación pre-cobro                                              #
    # ------------------------------------------------------------------ #

    def _compute_indexed_amount(self):
        """Hook: módulos consumidores override para devolver el nuevo
        ``transaction_amount`` indexado a aplicar antes del próximo cobro.

        Retorna:
        - ``float`` con el nuevo monto (en la moneda del preapproval), o
        - ``None`` si no hay indexación que aplicar (no toca el monto).

        El módulo base no indexa — devuelve ``None``. Implementaciones
        específicas (por ejemplo ``tupymeclara_subscription``) usan la
        offer asociada al sale_order para calcular el precio actual
        desde la pricelist y sus derivadas.
        """
        self.ensure_one()
        return None

    @api.model
    def _cron_index_amounts_before_charge(self, days_before=None, threshold_percent=None):
        """Cron diario que actualiza monto del preapproval antes del cobro.

        Para cada preapproval autorizado con ``next_payment_date`` igual a
        ``today + days_before``:

        1. Llama al hook ``_compute_indexed_amount`` para que el consumidor
           calcule el nuevo monto.
        2. Si el delta absoluto contra el ``transaction_amount`` actual
           supera ``threshold_percent``, hace ``PUT`` al preapproval con
           el nuevo monto.
        3. MP procesa el cambio y notifica al cliente automáticamente
           antes del próximo cobro.

        Idempotente vía ``X-Idempotency-Key`` derivado de
        ``(preapproval_id, target_date)`` — si el cron corre dos veces el
        mismo día, el segundo PUT devuelve el resultado del primero.

        Los parámetros se leen de ``ir.config_parameter``:

        - ``payment_mercado_pago_subscriptions.index_days_before`` (int,
          default 1) — días de anticipación al next_payment_date.
        - ``payment_mercado_pago_subscriptions.index_threshold_percent``
          (float, default 1.0) — delta mínimo en %.

        :param int days_before: override del config (opcional, para tests
            o invocación manual).
        :param float threshold_percent: override del config (opcional).
        """
        from datetime import timedelta
        icp = self.env['ir.config_parameter'].sudo()
        if days_before is None:
            days_before = int(icp.get_param(
                'payment_mercado_pago_subscriptions.index_days_before', '1'
            ))
        if threshold_percent is None:
            threshold_percent = float(icp.get_param(
                'payment_mercado_pago_subscriptions.index_threshold_percent', '1.0'
            ))
        target_date = fields.Date.today() + timedelta(days=days_before)
        candidates = self.search([
            ('status', '=', 'authorized'),
            ('next_payment_date', '!=', False),
        ])
        # Filtrar en Python por igualdad de fecha (ignorar hora).
        candidates = candidates.filtered(
            lambda p: p.next_payment_date and p.next_payment_date.date() == target_date
        )
        _logger.info(
            "MP cron index: %s preapprovals con cobro en %s (days_before=%s, threshold=%s%%).",
            len(candidates), target_date, days_before, threshold_percent,
        )
        for preapproval in candidates:
            try:
                preapproval._index_amount(threshold_percent=threshold_percent)
            except Exception as exc:  # noqa: BLE001
                _logger.exception(
                    "MP cron index: error sobre preapproval %s: %s",
                    preapproval.mp_id, exc,
                )
        return len(candidates)

    def _index_amount(self, threshold_percent=1.0):
        """Aplica la indexación a este preapproval específico.

        Calcula el nuevo monto via ``_compute_indexed_amount``, compara
        contra el actual, y si supera el umbral hace ``PUT``.

        Reutiliza la lógica de ``_mp_update_amount`` para la actualización
        en MP.
        """
        self.ensure_one()
        new_amount = self._compute_indexed_amount()
        if new_amount is None or new_amount <= 0:
            return False
        if not self.transaction_amount:
            return False
        delta_pct = abs(new_amount - self.transaction_amount) / self.transaction_amount * 100
        if delta_pct < threshold_percent:
            _logger.info(
                "MP cron index: preapproval %s delta %.2f%% bajo umbral %.2f%%, skip.",
                self.mp_id, delta_pct, threshold_percent,
            )
            return False
        idempotency_key = f"index_{self.mp_id}_{fields.Date.today().isoformat()}"
        self._mp_update_amount(new_amount, idempotency_key=idempotency_key)
        self.message_post(body=_(
            "Indexación pre-cobro: monto actualizado de %(old).2f a %(new).2f %(cur)s "
            "(delta %(delta).2f%%). MP notifica al cliente automáticamente.",
            old=self.transaction_amount,
            new=new_amount,
            cur=self.currency_id.name,
            delta=delta_pct,
        ))
        return True

    # ------------------------------------------------------------------ #
    #  Helpers                                                           #
    # ------------------------------------------------------------------ #

    def _apply_mp_payload(self, payload):
        """Aplica un payload de MP (response de POST/GET/PUT) al registro.

        Si el ``status`` del preapproval cambia, dispara el hook
        ``_on_status_changed(old_status, new_status)`` para que módulos
        consumidores reaccionen a transiciones (cancelled, paused,
        authorized). El hook solo se invoca cuando el status realmente
        cambia — escrituras idempotentes (mismo status) no lo disparan.
        """
        self.ensure_one()
        old_status = self.status
        values = {}
        if payload.get('id') and not self.mp_id:
            values['mp_id'] = payload['id']
        if payload.get('status'):
            values['status'] = payload['status']
        if payload.get('init_point'):
            values['init_point'] = payload['init_point']
        if payload.get('payer_id'):
            values['payer_id'] = str(payload['payer_id'])
        if payload.get('payer_first_name'):
            values['payer_first_name'] = payload['payer_first_name']
        if payload.get('payer_last_name'):
            values['payer_last_name'] = payload['payer_last_name']
        if payload.get('card_id'):
            values['mp_card_id'] = str(payload['card_id'])
        if payload.get('payment_method_id'):
            values['payment_method_id_mp'] = payload['payment_method_id']
        if payload.get('next_payment_date'):
            values['next_payment_date'] = payload['next_payment_date'].replace('T', ' ').rstrip('Z')[:19]

        auto = payload.get('auto_recurring') or {}
        if auto.get('transaction_amount') is not None:
            values['transaction_amount'] = float(auto['transaction_amount'])

        summarized = payload.get('summarized') or {}
        if summarized.get('last_charged_date'):
            values['last_charged_date'] = summarized['last_charged_date'].replace('T', ' ').rstrip('Z')[:19]
        if summarized.get('last_charged_amount') is not None:
            values['last_charged_amount'] = float(summarized['last_charged_amount'])
        if summarized.get('charged_amount') is not None:
            values['charged_amount_total'] = float(summarized['charged_amount'])
        if summarized.get('charged_quantity') is not None:
            values['charged_quantity'] = int(summarized['charged_quantity'])
        if summarized.get('pending_charge_quantity') is not None:
            values['pending_charge_quantity'] = int(summarized['pending_charge_quantity'])

        if values:
            self.write(values)

        # Hook de transición de estado. Solo si efectivamente cambió.
        new_status = self.status
        if 'status' in values and new_status and new_status != old_status:
            try:
                self._on_status_changed(old_status, new_status)
            except Exception as exc:  # noqa: BLE001
                _logger.exception(
                    "MP preapproval %s: error en _on_status_changed "
                    "(%s → %s): %s",
                    self.mp_id, old_status, new_status, exc,
                )

    # ------------------------------------------------------------------ #
    #  Hooks de transición de estado                                     #
    # ------------------------------------------------------------------ #

    def _on_status_changed(self, old_status, new_status):
        """Hook invocado cuando el ``status`` del preapproval cambia.

        Se dispara desde ``_apply_mp_payload`` cuando el status
        efectivamente cambia (no en escrituras idempotentes con el
        mismo status). Útil para reaccionar a transiciones específicas:

        - ``pending → authorized``: el cliente firmó. El consumidor
          puede activar funcionalidad SaaS.
        - ``authorized → cancelled``: el cliente canceló desde MP, o
          MP canceló tras 3 cobros fallidos consecutivos. El consumidor
          puede mandar email de despedida, marcar la cuenta para
          downgrade en T+30, etc.
        - ``authorized → paused``: el cliente pausó desde MP. El
          consumidor puede mantener acceso en read-only.

        El módulo base no hace nada — sólo loguea. Cualquier consumidor
        debe heredar este método con ``super()._on_status_changed(...)``
        para mantener composición.

        :param str old_status: status anterior (puede ser ``False`` /
            ``None`` si el preapproval no tenía status seteado).
        :param str new_status: status nuevo después del write.
        """
        for record in self:
            _logger.info(
                "MP preapproval %s status changed: %s → %s "
                "(no consumer hook).",
                record.mp_id or record.id, old_status, new_status,
            )
        return True
