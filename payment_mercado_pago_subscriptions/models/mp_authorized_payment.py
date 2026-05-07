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

from .. import const

_logger = logging.getLogger(__name__)


class MPAuthorizedPayment(models.Model):
    """Cuota recurrente generada por un preapproval en MP.

    Cada cuota nace como ``scheduled``, puede transitar por ``recycling``
    si MP reintenta tras un fallo, y termina como ``processed`` (con o
    sin éxito). Cada cuota está asociada a uno o varios ``payment``
    reales (``/v1/payments/{id}``) que son las transacciones efectivas.
    """
    _name = 'mp.authorized.payment'
    _description = 'Cuota recurrente Mercado Pago (authorized_payment)'
    _inherit = ['mail.thread']
    _order = 'create_date desc, id desc'

    name = fields.Char(
        compute='_compute_name',
        store=True,
    )
    preapproval_id = fields.Many2one(
        'mp.preapproval',
        string='Suscripción',
        required=True,
        ondelete='cascade',
        index=True,
    )
    provider_id = fields.Many2one(
        related='preapproval_id.provider_id',
        store=True,
    )
    mp_id = fields.Char(
        string='MP Authorized Payment ID',
        copy=False,
        index=True,
        readonly=True,
    )
    status = fields.Selection(
        [
            (const.AUTHORIZED_PAYMENT_STATUS_SCHEDULED, 'Programada'),
            (const.AUTHORIZED_PAYMENT_STATUS_RECYCLING, 'Reintentando'),
            (const.AUTHORIZED_PAYMENT_STATUS_PROCESSED, 'Procesada'),
        ],
        tracking=True,
        index=True,
    )
    debit_date = fields.Datetime(string='Fecha programada', readonly=True)
    transaction_amount = fields.Float(digits=(16, 2), readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)
    payment_id_mp = fields.Char(
        string='MP Payment ID',
        readonly=True,
        index=True,
        help='Pago real (recurso /v1/payments) generado por esta cuota.',
    )
    payment_status = fields.Char(
        string='Estado del pago real',
        readonly=True,
        help='approved, rejected, pending, in_process, refunded.',
    )
    retry_attempt = fields.Integer(string='Intento', readonly=True)
    invoice_id = fields.Many2one(
        'account.move',
        string='Factura Odoo',
        readonly=True,
        copy=False,
        help='account.move generado al confirmar la cuota como aprobada.',
    )

    _sql_constraints = [
        ('mp_id_uniq', 'unique(mp_id)', 'El MP Authorized Payment ID debe ser único.'),
    ]

    @api.depends('mp_id', 'status', 'preapproval_id.name')
    def _compute_name(self):
        for record in self:
            record.name = "%s — %s" % (
                record.preapproval_id.name or _('Suscripción'),
                record.mp_id or record.status or _('Cuota'),
            )

    def _apply_mp_payload(self, payload):
        """Aplica payload de MP (GET /authorized_payments/{id}) al registro."""
        self.ensure_one()
        values = {}
        if payload.get('id') and not self.mp_id:
            values['mp_id'] = str(payload['id'])
        if payload.get('status'):
            values['status'] = payload['status']
        if payload.get('debit_date'):
            values['debit_date'] = payload['debit_date'].replace('T', ' ').rstrip('Z')[:19]
        if payload.get('transaction_amount') is not None:
            values['transaction_amount'] = float(payload['transaction_amount'])
        if payload.get('currency_id'):
            currency = self.env['res.currency'].search(
                [('name', '=', payload['currency_id'])], limit=1
            )
            if currency:
                values['currency_id'] = currency.id
        if payload.get('payment') and payload['payment'].get('id'):
            values['payment_id_mp'] = str(payload['payment']['id'])
            if payload['payment'].get('status'):
                values['payment_status'] = payload['payment']['status']
        if payload.get('retry_attempt') is not None:
            values['retry_attempt'] = int(payload['retry_attempt'])

        if values:
            self.write(values)

    # ------------------------------------------------------------------ #
    #  Hooks de extensión para módulos consumidores                      #
    # ------------------------------------------------------------------ #

    def _on_processed_approved(self):
        """Hook invocado cuando una cuota cierra como ``processed`` con
        ``payment_status='approved'``.

        Es el punto de extensión canónico para que módulos consumidores
        (que asocian la suscripción MP a un modelo SaaS o a un sale.order
        específico) implementen la lógica post-cobro: generar factura,
        activar funcionalidad, enviar mail, etc.

        El módulo base no hace nada — sólo loguea. Cualquier consumidor
        debe heredar este método con ``super()._on_processed_approved()``
        para mantener composición.

        **Idempotencia**: este hook puede ser llamado múltiples veces
        para la misma cuota (re-entrega de webhook, cron de
        sincronización, dispatch manual). El consumidor debe ser
        robusto — chequear si ya generó la factura antes de duplicarla.
        """
        for record in self:
            _logger.info(
                "MP authorized_payment %s processed=approved (no consumer hook).",
                record.mp_id or record.id,
            )
        return True

    def _on_processed_rejected(self):
        """Hook invocado cuando una cuota cierra como ``processed`` con
        ``payment_status='rejected'``.

        Punto de extensión simétrico a ``_on_processed_approved`` para
        reaccionar al cobro fallido: enviar email al cliente con motivo
        del rechazo, marcar la cuenta SaaS en estado de retry, alertar
        al equipo comercial, etc.

        Política oficial de retry de MP (validada contra docs en docs.
        mercadopago.com.ar/developers/es/docs/subscriptions, sección
        "Lógica de reintentos de cobro"):

        - Cuando un cobro es rechazado, la cuota pasa a ``status='recycling'``
          (NO ``processed``). El webhook ``subscription_authorized_payment``
          se dispara pero NO entra en este hook (status != processed).
        - MP reintenta automáticamente hasta **4 veces** en una ventana
          de **10 días**.
        - Si alguno de los 4 reintentos resulta exitoso, la cuota pasa a
          ``processed`` con ``payment_status='approved'`` y se dispara
          ``_on_processed_approved`` (no este hook).
        - Si los 4 reintentos fallan o se vence la fecha de expiración,
          la cuota queda en ``processed`` con ``payment_status='rejected'``
          y SE DISPARA ESTE HOOK. Es el punto terminal de la cuota, NO
          va a haber más reintentos para esta misma cuota.
        - El próximo cobro mensual se programa normalmente.
        - Si **3 cuotas consecutivas** quedan rejected (3 meses con
          fallos), MP cancela el preapproval automáticamente y dispara
          ``subscription_preapproval`` con ``status='cancelled'`` →
          consumidor recibe via ``mp.preapproval._on_status_changed``.

        Implicancia importante: cuando se invoca este hook, la cuota
        actual ya se dio por perdida — el copy del email al cliente
        debe reflejar esto (no decir "MP va a reintentar"; ya reintentó
        y agotó las 4 oportunidades).

        El módulo base no hace nada — sólo loguea. Idempotente: puede
        invocarse múltiples veces por la misma cuota (re-entrega de
        webhook); el consumidor debe ser robusto.
        """
        for record in self:
            _logger.info(
                "MP authorized_payment %s processed=rejected "
                "(no consumer hook). retry_attempt=%s",
                record.mp_id or record.id, record.retry_attempt,
            )
        return True
