# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
##############################################################################
"""Constantes del proveedor Mercado Pago Suscripciones.

URLs, mapeos de estados y tópicos de webhook. Mantener este archivo libre
de imports de Odoo para que pueda ser consumido desde tests unitarios sin
levantar el ORM.
"""

# Endpoint base de la API de Mercado Pago (modo directo).
MP_API_BASE_URL = 'https://api.mercadopago.com'

# Rutas de webhooks expuestas por este módulo.
SUBSCRIPTIONS_WEBHOOK_ROUTE = '/payment/mercado_pago/subscriptions/webhook'

# Tópicos del webhook de suscripciones documentados por MP.
WEBHOOK_TOPIC_PREAPPROVAL = 'subscription_preapproval'
WEBHOOK_TOPIC_AUTHORIZED_PAYMENT = 'subscription_authorized_payment'
WEBHOOK_TOPIC_PAYMENT = 'payment'
WEBHOOK_TOPIC_PREAPPROVAL_PLAN = 'subscription_preapproval_plan'

WEBHOOK_TOPICS_HANDLED = {
    WEBHOOK_TOPIC_PREAPPROVAL,
    WEBHOOK_TOPIC_AUTHORIZED_PAYMENT,
    WEBHOOK_TOPIC_PAYMENT,
    WEBHOOK_TOPIC_PREAPPROVAL_PLAN,
}

# Estados del recurso preapproval de MP.
PREAPPROVAL_STATUS_PENDING = 'pending'
PREAPPROVAL_STATUS_AUTHORIZED = 'authorized'
PREAPPROVAL_STATUS_PAUSED = 'paused'
PREAPPROVAL_STATUS_CANCELLED = 'cancelled'
PREAPPROVAL_STATUS_FINISHED = 'finished'

PREAPPROVAL_STATUSES = (
    PREAPPROVAL_STATUS_PENDING,
    PREAPPROVAL_STATUS_AUTHORIZED,
    PREAPPROVAL_STATUS_PAUSED,
    PREAPPROVAL_STATUS_CANCELLED,
    PREAPPROVAL_STATUS_FINISHED,
)

# Estados del authorized_payment (cuotas recurrentes).
AUTHORIZED_PAYMENT_STATUS_SCHEDULED = 'scheduled'
AUTHORIZED_PAYMENT_STATUS_PROCESSED = 'processed'
AUTHORIZED_PAYMENT_STATUS_RECYCLING = 'recycling'

# Frecuencias soportadas por auto_recurring.
FREQUENCY_TYPE_DAYS = 'days'
FREQUENCY_TYPE_MONTHS = 'months'
FREQUENCY_TYPES = (FREQUENCY_TYPE_DAYS, FREQUENCY_TYPE_MONTHS)

# Tiempo máximo (segundos) que esperamos respuesta de MP por request HTTP.
DEFAULT_HTTP_TIMEOUT = 20

# Cantidad de reintentos en respuestas 5xx / timeout.
DEFAULT_HTTP_RETRIES = 3

# Backoff inicial entre reintentos (segundos). Se duplica en cada reintento.
DEFAULT_HTTP_BACKOFF_BASE = 2

# Header de idempotencia esperado por MP para POST mutadores.
HEADER_IDEMPOTENCY_KEY = 'X-Idempotency-Key'

# Header de firma del webhook que envía MP.
HEADER_WEBHOOK_SIGNATURE = 'x-signature'
HEADER_WEBHOOK_REQUEST_ID = 'x-request-id'
