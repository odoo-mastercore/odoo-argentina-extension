# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
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
        selection_add=[('dolarapi_ar', '[AR] dolarapi.com (BNA official / MEP bolsa)')],
    )

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
        """
        self.ensure_one()

        today = fields.Date.context_today(self)
        available_codes = set(available_currencies.mapped('name'))

        # Base ARS entry (needed for proper rebasing when company currency is ARS)
        result = {}
        if 'ARS' in available_codes:
            result['ARS'] = (1.0, today)

        # Only compute USD if active
        if 'USD' not in available_codes:
            return result

        icp = self.env['ir.config_parameter'].sudo()
        source = icp.get_param('dolarapi.com.data.source', 'oficial')  # oficial | bolsa

        url = f"https://dolarapi.com/v1/dolares/{source}"
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            _logger.exception("dolarapi provider error calling %s", url)
            raise UserError(_("Unable to retrieve exchange rate from dolarapi.com. Details: %s") % str(e))

        ars_per_usd = data.get('venta')
        if not ars_per_usd:
            raise UserError(_("dolarapi.com response did not include 'venta' rate."))

        try:
            ars_per_usd = float(ars_per_usd)
        except Exception as e:  # noqa: BLE001
            raise UserError(_("Invalid 'venta' value received from dolarapi.com: %s") % str(e))

        if ars_per_usd <= 0:
            raise UserError(_("Invalid 'venta' rate received from dolarapi.com (must be > 0)."))

        # USD rate expressed vs ARS base (consistent with other providers using inverse convention)
        result['USD'] = (1.0 / ars_per_usd, today)
        return result