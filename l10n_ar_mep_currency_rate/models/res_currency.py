# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
#
###############################################################################
from odoo import models, fields, api, registry, SUPERUSER_ID, _
from datetime import datetime
import requests
import psycopg2


class ResCurrency(models.Model):
    _inherit = 'res.currency'


    def _log_error(self, message):
        db_name = self._cr.dbname
        try:
            db_registry = registry(db_name)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['ir.logging'].sudo().create({
                    'name': 'res.currency',
                    'type': 'server',
                    'dbname': db_name,
                    'level': 'ERROR',
                    'message': message,
                    'path': '0',
                    'func': 'set_mep_currency_rate',
                    'line': '0'
                })
        except psycopg2.Error:
            pass

    @api.model
    def set_mep_currency_rate(self):
        fecha = fields.Date.context_today(self, datetime.today())
        usd_id = self.env.ref('base.USD').id
        try:
            companies_ar = self.env['res.company'].search([
                ('account_fiscal_country_id', '=', self.env.ref('base.ar').id),
                ('currency_id', 'in', [self.env.ref('base.ARS').id])
            ])

            if companies_ar:
                # Llamada a la API
                # Posibles valores de parámetro dolarapi.com.data.source:
                # - "oficial" : Cambio BNA
                # - "bolsa" : Cambio MEP
                source = self.env['ir.config_parameter'].get_param('dolarapi.com.data.source', 'oficial')
                response = requests.get("https://dolarapi.com/v1/dolares/"+source)
                if response.status_code == 200:
                    data = response.json()
                    exchange_rate = data.get('venta', 0)  # Toma el valor de 'venta'

                    if exchange_rate:
                        for company in companies_ar:
                            vals = {
                                'name': fecha,
                                'company_id': company.id,
                                'inverse_company_rate': exchange_rate or 1,
                                'currency_id': usd_id,
                            }
                            new_rate = self.env['res.currency.rate'].search([
                                ('name', '=', fecha),
                                ('currency_id', '=', usd_id),
                                ('company_id', '=', company.id)
                            ])
                            if not new_rate:
                                self.env['res.currency.rate'].create(vals)
                            else:
                                new_rate.write(vals)
                    else:
                        self._log_error("No se pudo obtener la tasa de cambio de la API.")
                else:
                    self._log_error(f"Error {response.status_code} al consultar la API: {response.text}")

        except Exception as e:
            self._log_error(f'Problema llamando a https://dolarapi.com/v1/dolares/bolsa: {str(e)}')
