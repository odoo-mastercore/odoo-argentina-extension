# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
##############################################################################

{
    'name': 'Payment Provider: Mercado Pago Subscriptions *',
    'version': '19.0.0.4.1',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': 'Suscripciones recurrentes con Mercado Pago (preapproval) sobre sale_subscription.',
    'description': """
Implementación del recurso Suscripciones de Mercado Pago (preapproval +
preapproval_plan) sobre el módulo nativo payment_mercado_pago (CE) y
sale_subscription (EE).

Características principales:

- Cobro recurrente con autorización explícita del suscriptor (preapproval).
- Catálogo de planes (preapproval_plan) sincronizado con MP.
- Webhook firmado HMAC-SHA256 para tres tópicos: subscription_preapproval,
  subscription_authorized_payment y payment.
- Bypass del proxy mercadopago.api.odoo.com: opera contra
  api.mercadopago.com con credenciales propias del comercio.
- Modificación de monto on-demand (PUT /preapproval/{id}) para indexación.
- Compatible con la máquina de estados de sale_subscription.

El módulo es genérico: no asume pricing, ofertas SaaS específicas ni
indexación a una moneda particular. Esa lógica vive en módulos consumidores
(por ejemplo tupymeclara_subscription).
    """,
    'author': 'Mastercore Sinapsys Global®',
    'website': 'https://www.mastercore.us',
    'license': 'OPL-1',
    'depends': [
        'payment_mercado_pago',
        'sale_subscription',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/payment_provider_views.xml',
        'views/mp_preapproval_plan_views.xml',
        'views/mp_preapproval_views.xml',
        'views/mp_authorized_payment_views.xml',
        'views/sale_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
