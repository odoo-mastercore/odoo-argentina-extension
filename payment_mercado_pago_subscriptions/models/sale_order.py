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


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    mp_preapproval_id = fields.Many2one(
        'mp.preapproval',
        string='Suscripción Mercado Pago',
        copy=False,
        index=True,
        ondelete='set null',
        help='Suscripción MP (preapproval) asociada a esta orden. Cuando '
             'está seteado, el cobro recurrente lo gestiona MP y el cron '
             'nativo de sale_subscription se omite.',
    )
    mp_preapproval_status = fields.Selection(
        related='mp_preapproval_id.status',
        store=True,
        string='Estado MP',
    )
    mp_init_point = fields.Char(
        related='mp_preapproval_id.init_point',
        string='URL de firma MP',
    )
    mp_next_payment_date = fields.Datetime(
        related='mp_preapproval_id.next_payment_date',
        string='Próximo cobro MP',
        store=True,
    )

    def _mp_create_preapproval(
        self,
        plan=None,
        amount=None,
        currency=None,
        reason=None,
        payer_email=None,
        external_reference=None,
        back_url=None,
        card_token_id=None,
        provider=None,
    ):
        """Crea el ``mp.preapproval`` asociado a esta orden y lo sincroniza con MP.

        Es la API pública que los módulos consumidores invocan al iniciar
        el flow de checkout de suscripción. Acepta plan opcional (catálogo)
        o monto/moneda directos (sin plan).

        :param mp.preapproval.plan plan: plan asociado (opcional).
        :param float amount: monto por ciclo (si no hay plan, requerido).
        :param res.currency currency: moneda (si no hay plan, requerido).
        :param str reason: texto visible al suscriptor.
        :param str payer_email: mail del suscriptor.
        :param str external_reference: para idempotencia.
        :param str back_url: URL de retorno post-firma.
        :param str card_token_id: token de tarjeta efímero (modo B
            authorized desde el alta). Si no se pasa, queda en modo A
            hosted (status=pending).
        :param payment.provider provider: provider MP a usar. Si se omite,
            busca el primer provider mercado_pago con mp_use_direct_api.
        :return: ``mp.preapproval`` creado.
        """
        self.ensure_one()
        if self.mp_preapproval_id:
            raise UserError(_(
                "La orden %s ya tiene una suscripción MP asociada.", self.name
            ))

        if not provider:
            provider = self.env['payment.provider'].search([
                ('code', '=', 'mercado_pago'),
                ('mp_use_direct_api', '=', True),
                ('state', '=', 'enabled'),
                ('company_id', 'in', [False, self.company_id.id]),
            ], limit=1)
        if not provider:
            raise UserError(_(
                "No hay provider Mercado Pago en modo directo activo para esta compañía."
            ))

        if plan:
            amount = amount or plan.transaction_amount
            currency = currency or plan.currency_id
            reason = reason or plan.reason
            back_url = back_url or plan.back_url
        else:
            if not amount or not currency:
                raise UserError(_(
                    "Sin plan asociado debe proveerse monto y moneda."
                ))

        if not reason:
            reason = _("Suscripción %s", self.name)
        if not back_url:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            back_url = f"{base_url}/my/orders/{self.id}"
        if not payer_email:
            payer_email = self.partner_id.email
        if not payer_email:
            raise UserError(_(
                "El cliente %s no tiene email; es requerido para crear la suscripción.",
                self.partner_id.display_name,
            ))
        if not external_reference:
            external_reference = f"so_{self.id}"

        preapproval = self.env['mp.preapproval'].create({
            'provider_id': provider.id,
            'plan_id': plan.id if plan else False,
            'reason': reason,
            'payer_email': payer_email,
            'external_reference': external_reference,
            'transaction_amount': amount,
            'currency_id': currency.id,
            'back_url': back_url,
            'card_token_id_value': card_token_id or False,
            'sale_order_id': self.id,
            'auto_recurring_frequency': plan.frequency if plan else 1,
            'auto_recurring_frequency_type': plan.frequency_type if plan else const.FREQUENCY_TYPE_MONTHS,
        })
        preapproval.action_create_in_mp()
        self.mp_preapproval_id = preapproval.id
        return preapproval

    # ------------------------------------------------------------------ #
    #  Override del cron de cobro de sale_subscription                   #
    # ------------------------------------------------------------------ #

    def _create_recurring_invoice(self, batch_size=30):
        """Skipea las órdenes con preapproval MP activo.

        Cuando una suscripción Odoo está delegada a Mercado Pago, la
        factura no debe emitirse por el cron nativo: la generamos
        recién cuando MP reporta ``subscription_authorized_payment``
        en estado ``processed=approved`` vía webhook.

        Esto evita doble cobro, facturas que después no cobran y
        desincronización entre Odoo y MP.
        """
        orders_with_mp = self.filtered(
            lambda so: so.mp_preapproval_id
            and so.mp_preapproval_id.status in (
                const.PREAPPROVAL_STATUS_AUTHORIZED,
                const.PREAPPROVAL_STATUS_PAUSED,
                const.PREAPPROVAL_STATUS_PENDING,
            )
        )
        orders_without_mp = self - orders_with_mp
        return super(SaleOrder, orders_without_mp)._create_recurring_invoice(
            batch_size=batch_size
        )
