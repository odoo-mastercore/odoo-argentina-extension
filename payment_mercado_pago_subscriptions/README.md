# Payment Provider: Mercado Pago Subscriptions

Implementación del recurso **Suscripciones de Mercado Pago** (`preapproval`
+ `preapproval_plan`) sobre los módulos nativos `payment_mercado_pago` (CE)
y `sale_subscription` (EE) en Odoo 19.

## Por qué este módulo existe

El módulo nativo `payment_mercado_pago` cubre:

- Checkout Pro one-shot (redirect hosted).
- Pago directo con tarjeta (tokenización).
- Webhook de pagos individuales (`/v1/payments`).

Pero **no implementa** el recurso de Suscripciones, que es la API
oficialmente soportada por MP para cobro recurrente con:

- Autorización explícita del suscriptor (mejor que MIT con token guardado).
- Dunning automático y reintentos administrados por MP.
- Account updater (parcial) para tarjetas reemitidas.
- Saldo MP / billetera / QR como medios de pago en el checkout.

Este módulo cubre ese hueco implementando el contrato `preapproval` +
`preapproval_plan` y enchufándolo al ciclo de `sale_subscription` para que
las suscripciones Odoo se cobren automáticamente por MP sin intervención
del cron nativo.

## Características

- **API directa a `api.mercadopago.com`** con `access_token` propio del
  comercio. Bypasea el proxy `mercadopago.api.odoo.com` para que la
  relación contractual sea directa.
- **Webhook firmado** HMAC-SHA256 (header `x-signature`) con validación
  obligatoria.
- **Tres tópicos manejados**: `subscription_preapproval`,
  `subscription_authorized_payment`, `payment`.
- **Idempotencia** con `X-Idempotency-Key` en todos los `POST` mutadores.
- **Retry exponencial** con backoff en respuestas 5xx / timeout.
- **Override del cron de cobro** de `sale_subscription` para órdenes con
  `mp_preapproval_id`: la factura se emite al recibir
  `subscription_authorized_payment.processed=approved`.
- **Modificación de monto** vía `PUT /preapproval/{id}` (útil para
  indexación de pricing por moneda fluctuante).

## Instalación

```bash
# Como submodule (Odoo.sh):
git submodule add git@github.com:odoo-mastercore/odoo-argentina-extension.git \
    odoo-mastercore/odoo-argentina-extension

# O agregando al addons_path:
addons_path = /opt/odoo/custom/odoo-argentina-extension
```

Dependencias:

- `payment_mercado_pago` (Odoo 19 CE)
- `sale_subscription` (Odoo 19 EE)

## Configuración

1. **Crear app de MP** en
   [Tus integraciones](https://www.mercadopago.com.ar/developers/panel)
   con tipo "Pagos online" → "Suscripciones".
2. Generar credenciales TEST y PRODUCCIÓN.
3. **Activar el provider Mercado Pago** en Odoo
   (`Contabilidad → Configuración → Proveedores de pago`).
4. Marcar **`Modo directo`** (campo agregado por este módulo) y pegar el
   `access_token` propio.
5. Configurar **webhook URL** en el panel MP apuntando a
   `https://<tu-dominio>/payment/mercado_pago/subscriptions/webhook`.
6. Pegar el **secret del webhook** generado por MP en el provider.
7. Suscribirse a los tópicos: `subscription_preapproval`,
   `subscription_authorized_payment`, `payment`.

## Uso programático (consumidores del módulo)

```python
# Crear plan en MP desde un módulo consumidor
plan = env['mp.preapproval.plan'].create({
    'provider_id': provider.id,
    'reason': 'Mi SaaS — Plan Pro',
    'frequency': 1,
    'frequency_type': 'months',
    'transaction_amount': 60000.0,
    'currency_id': env.ref('base.ARS').id,
    'back_url': 'https://misitio.com/return',
})
plan.action_sync_to_mp()  # Crea el recurso en MP y persiste mp_id.

# Crear preapproval (sin firmar todavía)
order = env['sale.order'].browse(...)
preapproval = order._mp_create_preapproval(
    plan=plan,
    payer_email='cliente@ejemplo.com',
    external_reference=f'so_{order.id}',
)
# preapproval.init_point → redirigir al cliente para que firme.

# Modificar monto (indexación)
preapproval._mp_update_amount(new_amount=68900.0)
```

## Testing en sandbox

Tarjetas y cuentas de prueba: ver
[documentación de tarjetas de prueba de MP](https://www.mercadopago.com.ar/developers/es/docs/checkout-api/integration-test/test-cards).

## Licencia

OPL-1 (Odoo Proprietary License v1.0).
Copyright © 2026 Mastercore Sinapsys Global®.
