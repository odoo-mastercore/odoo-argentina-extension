# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
# See https://www.gnu.org/licenses/agpl-3.0.html
#
###############################################################################

import logging
import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = 'res.company'

    currency_provider = fields.Selection(
        selection_add=[('dolarapi_ar', '[AR] dolarapi.com (oficial BNA / mayorista / MEP bolsa)')],
    )

    _DOLARAPI_VALID_SOURCES = ('oficial', 'mayorista', 'bolsa')

    @api.model
    def fetch_dolarapi_rate(self, source='bolsa', timeout=20):
        """Consultador independiente de dolarapi.com.

        No depende de la configuración de ``currency_provider`` de la
        compañía ni del cron de ``currency_rate_live``. Pensado para
        que otros módulos consulten cotizaciones específicas
        (típicamente MEP/bolsa para indexación de precios) sin afectar
        la cotización contable de la instancia.

        :param str source: Fuente de cotización, una de ``oficial``
            (BNA), ``mayorista`` o ``bolsa`` (MEP/CCL). Default:
            ``'bolsa'`` (MEP).
        :param int timeout: Timeout HTTP en segundos. Default: 20.
        :return: dict con keys:

            - ``compra`` (float): ARS por USD (compra).
            - ``venta`` (float): ARS por USD (venta).
            - ``fecha_actualizacion`` (str): timestamp ISO 8601
              reportado por dolarapi.com.
            - ``casa`` (str): identificador de la fuente.
            - ``nombre`` (str): etiqueta humana de la fuente.

        :raises UserError: si la fuente es inválida, la API no
            responde, o el payload no contiene campos esperados.
        """
        if source not in self._DOLARAPI_VALID_SOURCES:
            raise UserError(_(
                "Invalid dolarapi source: %(source)s. Valid: %(valid)s.",
                source=source,
                valid=', '.join(self._DOLARAPI_VALID_SOURCES),
            ))
        url = f"https://dolarapi.com/v1/dolares/{source}"
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            _logger.exception("dolarapi fetch error calling %s", url)
            raise UserError(_(
                "Unable to retrieve exchange rate from dolarapi.com. Details: %s"
            ) % str(e))

        for required in ('venta', 'compra', 'fechaActualizacion'):
            if required not in data:
                raise UserError(_(
                    "dolarapi.com response is missing required field: %s"
                ) % required)

        try:
            compra = float(data['compra'])
            venta = float(data['venta'])
        except Exception as e:  # noqa: BLE001
            raise UserError(_(
                "Invalid numeric values received from dolarapi.com: %s"
            ) % str(e))

        if venta <= 0 or compra <= 0:
            raise UserError(_(
                "Invalid rates received from dolarapi.com (must be > 0). "
                "compra=%(c)s venta=%(v)s",
                c=compra, v=venta,
            ))

        return {
            'compra': compra,
            'venta': venta,
            'fecha_actualizacion': data['fechaActualizacion'],
            'casa': data.get('casa', source),
            'nombre': data.get('nombre', source),
        }

    def _parse_dolarapi_ar_data(self, available_currencies):
        """
        Provider for Argentina using https://dolarapi.com

        Expected output format:
            { 'ARS': (1.0, date), 'USD': (rate_vs_company_currency, date) }

        Notes:
        - dolarapi returns ARS per 1 USD (venta).
        - Odoo expects rates relative to the company currency in a normalized way,
          and currency_rate_live will rebase on company currency. We return:
            ARS = 1.0
            USD = 1 / (ARS_per_USD)

        Implementation: delegates the HTTP call to ``fetch_dolarapi_rate`` so
        the public consumer API and the currency_rate_live provider share the
        same request and validation logic.
        """
        self.ensure_one()
        today = fields.Date.context_today(self)

        # Validate availability
        available_currency_names = set(
            available_currencies.mapped('name')
            if hasattr(available_currencies, 'mapped')
            else available_currencies
        )
        if 'USD' not in available_currency_names:
            raise UserError(_("USD is not available in the selected currencies."))
        if self.currency_id.name != 'ARS':
            raise UserError(_("This provider is intended for ARS-based companies."))

        icp = self.env['ir.config_parameter'].sudo()
        source = icp.get_param('dolarapi.com.data.source', 'oficial')  # oficial | mayorista | bolsa

        rate_data = self.fetch_dolarapi_rate(source=source)
        ars_per_usd = rate_data['venta']

        result = {'ARS': (1.0, today)}
        # USD rate expressed vs ARS base (consistent with other providers using inverse convention)
        result['USD'] = (1.0 / ars_per_usd, today)
        return result
