# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
# See https://www.gnu.org/licenses/agpl-3.0.html
#
##############################################################################

from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase


class DolarApiResponse:

    def raise_for_status(self):
        return None

    def json(self):
        return {
            'moneda': 'USD',
            'casa': 'mayorista',
            'nombre': 'Mayorista',
            'compra': 1395.5,
            'venta': 1404.5,
            'fechaActualizacion': '2026-04-28T15:47:00.000Z',
        }


class TestDolarApiProvider(TransactionCase):

    def test_parse_dolarapi_mayorista_source(self):
        source_selection = dict(
            self.env['res.config.settings']._fields['dolarapi_data_source'].selection
        )
        self.assertEqual(source_selection['mayorista'], 'Mayorista')

        ars = self.env.ref('base.ARS')
        usd = self.env.ref('base.USD')
        company = self.env['res.company'].create({
            'name': 'DolarAPI AR',
            'currency_id': ars.id,
            'currency_provider': 'dolarapi_ar',
        })
        self.env['ir.config_parameter'].sudo().set_param('dolarapi.com.data.source', 'mayorista')

        with patch(
            'odoo.addons.l10n_ar_currency_rate_dolarapi.models.res_company.requests.get',
            return_value=DolarApiResponse(),
        ) as mock_get:
            rates = company._parse_dolarapi_ar_data(ars | usd)

        mock_get.assert_called_once_with('https://dolarapi.com/v1/dolares/mayorista', timeout=20)
        self.assertEqual(rates['ARS'], (1.0, fields.Date.context_today(company)))
        self.assertEqual(rates['USD'], (1.0 / 1404.5, fields.Date.context_today(company)))
