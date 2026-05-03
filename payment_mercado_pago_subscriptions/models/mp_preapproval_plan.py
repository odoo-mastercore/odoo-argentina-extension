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

from .. import const


class MPPreapprovalPlan(models.Model):
    """Catálogo de planes de suscripción registrados en Mercado Pago.

    Espejo local de ``preapproval_plan``. Cada registro de este modelo
    corresponde a un plan creado en MP. Los módulos consumidores (por
    ejemplo el catálogo de ofertas SaaS de tupymeclara) referencian
    estos planes para asociar suscripciones nuevas.

    El registro local se crea primero y luego se sincroniza a MP con
    ``action_sync_to_mp`` (POST /preapproval_plan). El ``mp_id`` queda
    persistido para invocaciones futuras.
    """
    _name = 'mp.preapproval.plan'
    _description = 'Plan de suscripción Mercado Pago (preapproval_plan)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(required=True, tracking=True)
    provider_id = fields.Many2one(
        'payment.provider',
        string='Proveedor de pago',
        required=True,
        domain="[('code', '=', 'mercado_pago')]",
        ondelete='restrict',
        tracking=True,
    )
    mp_id = fields.Char(
        string='MP Plan ID',
        copy=False,
        index=True,
        readonly=True,
        tracking=True,
        help='ID del preapproval_plan en Mercado Pago. Vacío significa que '
             'todavía no se sincronizó a MP.',
    )
    reason = fields.Char(
        required=True,
        tracking=True,
        help='Texto que ve el suscriptor en el checkout y notificaciones MP.',
    )
    frequency = fields.Integer(
        required=True,
        default=1,
        tracking=True,
        help='Cantidad de unidades por ciclo (junto con frequency_type).',
    )
    frequency_type = fields.Selection(
        [
            (const.FREQUENCY_TYPE_DAYS, 'Días'),
            (const.FREQUENCY_TYPE_MONTHS, 'Meses'),
        ],
        required=True,
        default=const.FREQUENCY_TYPE_MONTHS,
        tracking=True,
    )
    repetitions = fields.Integer(
        string='Repeticiones',
        help='Cantidad total de ciclos. 0 o vacío = suscripción indefinida.',
    )
    billing_day = fields.Integer(
        string='Día de cobro',
        help='Día fijo del mes (sólo si frequency_type=meses). Vacío = el '
             'mismo día que la firma del preapproval.',
    )
    billing_day_proportional = fields.Boolean(
        string='Prorrateo del primer ciclo',
        help='Cobra fracción al alta para alinear todas las suscripciones al '
             'billing_day. Sólo aplica si billing_day está seteado.',
    )
    free_trial_frequency = fields.Integer(string='Trial — duración')
    free_trial_frequency_type = fields.Selection(
        [
            (const.FREQUENCY_TYPE_DAYS, 'Días'),
            (const.FREQUENCY_TYPE_MONTHS, 'Meses'),
        ],
        string='Trial — unidad',
    )
    transaction_amount = fields.Float(
        string='Monto por ciclo',
        required=True,
        digits=(16, 2),
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        tracking=True,
        help='Moneda del cobro. En Argentina típicamente ARS.',
    )
    back_url = fields.Char(
        required=True,
        tracking=True,
        help='URL de retorno post autorización del usuario.',
    )
    external_reference = fields.Char(
        copy=False,
        tracking=True,
        help='Referencia externa del comercio. Útil para reconciliación.',
    )
    payment_methods_credit_card = fields.Boolean(
        string='Acepta tarjeta de crédito',
        default=True,
    )
    payment_methods_debit_card = fields.Boolean(
        string='Acepta tarjeta de débito',
        default=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('active', 'Activo en MP'),
            ('inactive', 'Inactivo en MP'),
        ],
        default='draft',
        required=True,
        copy=False,
        tracking=True,
    )
    init_point = fields.Char(
        string='URL de firma',
        copy=False,
        readonly=True,
        help='URL hosted donde el suscriptor inicia el flow de firma.',
    )
    preapproval_ids = fields.One2many(
        'mp.preapproval',
        'plan_id',
        string='Suscripciones generadas',
    )
    preapproval_count = fields.Integer(
        compute='_compute_preapproval_count',
        string='Suscripciones',
    )

    _sql_constraints = [
        ('mp_id_uniq', 'unique(mp_id)', 'El MP Plan ID debe ser único.'),
    ]

    @api.depends('preapproval_ids')
    def _compute_preapproval_count(self):
        for plan in self:
            plan.preapproval_count = len(plan.preapproval_ids)

    def _build_mp_payload(self):
        """Arma el payload para POST /preapproval_plan a partir del registro."""
        self.ensure_one()
        auto_recurring = {
            'frequency': self.frequency,
            'frequency_type': self.frequency_type,
            'transaction_amount': self.transaction_amount,
            'currency_id': self.currency_id.name,
        }
        if self.repetitions:
            auto_recurring['repetitions'] = self.repetitions
        if self.billing_day:
            auto_recurring['billing_day'] = self.billing_day
            auto_recurring['billing_day_proportional'] = bool(self.billing_day_proportional)
        if self.free_trial_frequency and self.free_trial_frequency_type:
            auto_recurring['free_trial'] = {
                'frequency': self.free_trial_frequency,
                'frequency_type': self.free_trial_frequency_type,
            }

        payment_types = []
        if self.payment_methods_credit_card:
            payment_types.append({'id': 'credit_card'})
        if self.payment_methods_debit_card:
            payment_types.append({'id': 'debit_card'})

        payload = {
            'reason': self.reason,
            'auto_recurring': auto_recurring,
            'back_url': self.back_url,
            'payment_methods_allowed': {
                'payment_types': payment_types or [{}],
                'payment_methods': [{}],
            },
        }
        if self.external_reference:
            payload['external_reference'] = self.external_reference
        return payload

    def action_sync_to_mp(self):
        """Crea o actualiza el plan en Mercado Pago.

        Si el registro local todavía no tiene ``mp_id``, hace ``POST``
        nuevo. Si ya tiene, hace ``PUT`` para actualizar campos
        modificables (monto, estado).
        """
        for plan in self:
            client = plan.provider_id._mp_get_client()
            payload = plan._build_mp_payload()
            if plan.mp_id:
                response = client.update_preapproval_plan(plan.mp_id, payload)
            else:
                response = client.create_preapproval_plan(payload)
                plan.mp_id = response.get('id')
            plan.write({
                'state': 'active' if response.get('status') == 'active' else 'inactive',
                'init_point': response.get('init_point') or plan.init_point,
            })
            plan.message_post(body=_(
                "Plan sincronizado con MP. ID=%(id)s, status=%(status)s.",
                id=response.get('id'), status=response.get('status'),
            ))
        return True

    def action_view_preapprovals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Suscripciones'),
            'res_model': 'mp.preapproval',
            'view_mode': 'list,form',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id, 'default_provider_id': self.provider_id.id},
        }
