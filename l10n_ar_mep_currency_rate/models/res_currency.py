# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3 
#
###############################################################################

from odoo import models, fields, api, _
from datetime import datetime
import requests

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def set_mep_currency_rate(self):
        fecha = fields.Date.context_today(self, datetime.today())
        usd_id = self.env.ref('base.USD').id

        def log_error(message):
            """Función para registrar errores en ir_logging."""
            with self.pool.cursor() as cr:
                cr.execute("""
                    INSERT INTO ir_logging(create_date, create_uid, type, dbname, name, level, message, path, line, func)
                    VALUES (NOW() at time zone 'UTC', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (self.env.uid, 'server', self._cr.dbname, __name__, 'error', message, "action", 0, 'set_mep_currency_rate'))

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
                        log_error("No se pudo obtener la tasa de cambio de la API.")
                else:
                    log_error(f"Error {response.status_code} al consultar la API: {response.text}")

        except Exception as e:
            log_error(f'Problema llamando a https://dolarapi.com/v1/dolares/bolsa: {str(e)}')
