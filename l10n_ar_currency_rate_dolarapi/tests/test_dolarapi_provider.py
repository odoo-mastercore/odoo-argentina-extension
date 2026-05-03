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
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class DolarApiResponse:

    def __init__(self, payload=None):
        self._payload = payload or {
            'moneda': 'USD',
            'casa': 'mayorista',
            'nombre': 'Mayorista',
            'compra': 1395.5,
            'venta': 1404.5,
            'fechaActualizacion': '2026-04-28T15:47:00.000Z',
        }

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


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


class TestDolarApiPublicFetch(TransactionCase):
    """Tests del método público fetch_dolarapi_rate que consume cualquier módulo."""

    def test_fetch_default_source_is_bolsa(self):
        bolsa_payload = {
            'moneda': 'USD',
            'casa': 'bolsa',
            'nombre': 'Bolsa',
            'compra': 1380.0,
            'venta': 1390.0,
            'fechaActualizacion': '2026-05-02T16:00:00.000Z',
        }
        with patch(
            'odoo.addons.l10n_ar_currency_rate_dolarapi.models.res_company.requests.get',
            return_value=DolarApiResponse(bolsa_payload),
        ) as mock_get:
            result = self.env['res.company'].fetch_dolarapi_rate()

        mock_get.assert_called_once_with('https://dolarapi.com/v1/dolares/bolsa', timeout=20)
        self.assertEqual(result['compra'], 1380.0)
        self.assertEqual(result['venta'], 1390.0)
        self.assertEqual(result['casa'], 'bolsa')
        self.assertEqual(result['nombre'], 'Bolsa')
        self.assertEqual(result['fecha_actualizacion'], '2026-05-02T16:00:00.000Z')

    def test_fetch_explicit_oficial(self):
        oficial_payload = {
            'casa': 'oficial', 'nombre': 'Oficial',
            'compra': 950.0, 'venta': 970.0,
            'fechaActualizacion': '2026-05-02T16:00:00.000Z',
        }
        with patch(
            'odoo.addons.l10n_ar_currency_rate_dolarapi.models.res_company.requests.get',
            return_value=DolarApiResponse(oficial_payload),
        ) as mock_get:
            result = self.env['res.company'].fetch_dolarapi_rate(source='oficial')

        mock_get.assert_called_once_with('https://dolarapi.com/v1/dolares/oficial', timeout=20)
        self.assertEqual(result['venta'], 970.0)

    def test_fetch_invalid_source_raises(self):
        with self.assertRaises(UserError):
            self.env['res.company'].fetch_dolarapi_rate(source='unknown')

    def test_fetch_missing_required_field_raises(self):
        bad_payload = {'casa': 'bolsa', 'nombre': 'Bolsa'}  # sin venta/compra/fechaActualizacion
        with patch(
            'odoo.addons.l10n_ar_currency_rate_dolarapi.models.res_company.requests.get',
            return_value=DolarApiResponse(bad_payload),
        ):
            with self.assertRaises(UserError):
                self.env['res.company'].fetch_dolarapi_rate()

    def test_fetch_zero_rate_raises(self):
        zero_payload = {
            'casa': 'bolsa', 'nombre': 'Bolsa',
            'compra': 0.0, 'venta': 0.0,
            'fechaActualizacion': '2026-05-02T16:00:00.000Z',
        }
        with patch(
            'odoo.addons.l10n_ar_currency_rate_dolarapi.models.res_company.requests.get',
            return_value=DolarApiResponse(zero_payload),
        ):
            with self.assertRaises(UserError):
                self.env['res.company'].fetch_dolarapi_rate()
