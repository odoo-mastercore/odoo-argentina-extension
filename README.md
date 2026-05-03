# odoo-argentina-extension

Módulos Odoo de Mastercore Sinapsys Global® para extender la localización
argentina de Odoo y la operación SaaS sobre el mercado AR/LATAM.

Cada módulo declara su propia licencia en `__manifest__.py`. La convivencia
de licencias dentro del mismo repositorio es deliberada y legalmente válida:
los módulos son artefactos independientes, distribuidos uno por uno.

## Versiones soportadas

| Versión Odoo | Branch |
|---|---|
| 19.0 | `19.0` (activa) |
| 18.0 | `18.0` |
| 17.0 | `17.0` |

## Módulos

### `l10n_ar_currency_rate_dolarapi`

Proveedor de cotización USD/ARS para Argentina basado en
[dolarapi.com](https://dolarapi.com), integrado al framework
`currency_rate_live` de Odoo Enterprise.

- Fuentes soportadas: oficial (BNA), mayorista, bolsa (MEP/CCL).
- Configurable desde Ajustes.
- Expone método público `res.company.fetch_dolarapi_rate(source='bolsa')`
  para que otros módulos consulten cotizaciones específicas sin afectar la
  cotización contable de la instancia.
- **Licencia**: AGPL-3.

### `l10n_ar_hr_payroll`

Extensiones a la nómina argentina sobre `hr_payroll` (EE).

- **Licencia**: ver `__manifest__.py` del módulo.

### `payment_mercado_pago_subscriptions`

Implementación del recurso **Suscripciones de Mercado Pago**
(`preapproval` + `preapproval_plan`) sobre los módulos nativos
`payment_mercado_pago` (CE) y `sale_subscription` (EE).

Permite cobrar suscripciones recurrentes con autorización explícita del
suscriptor, dunning automático gestionado por MP, y auto-actualización de
tarjetas. Funciona contra `api.mercadopago.com` con `access_token` propio
del comercio (sin pasar por el proxy de Odoo S.A.).

- **Estado**: en desarrollo activo.
- **Licencia**: OPL-1 (Odoo Proprietary License v1.0).

## Instalación

Cada módulo se instala desde Apps de Odoo después de agregar este
repositorio al `addons_path` (o como submodule en proyectos Odoo.sh).

## Autor

Mastercore Sinapsys Global® · [mastercore.us](https://www.mastercore.us)

## Soporte

Issues y feature requests: usar el tracker de GitHub del repositorio.
Soporte comercial sobre los módulos OPL-1: contacto vía
[mastercore.us](https://www.mastercore.us).
