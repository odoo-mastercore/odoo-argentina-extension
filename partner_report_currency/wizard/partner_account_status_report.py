###############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2022-Present.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################

import json
import ssl
import urllib
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlretrieve, install_opener
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import requests
import logging

_logger = logging.getLogger(__name__)

class partnerAccountStatusReport(models.TransientModel):
    _name = 'partner.account.status.report'

    partner_id = fields.Many2one('res.partner', string='Partner')
    company_id = fields.Many2one('res.company', string='Compañía')

    def _get_report_base_filename(self):
        return 'Estado_de_cuenta' + '_' + self.partner_id.name.replace(' ', '_')

    def _default_start_date(self):
        return datetime.now()

    start_date = fields.Date(string='Fecha de inicio', required=True, default=_default_start_date)
    end_date = fields.Date(string='Fecha fin', required=True, default=fields.Datetime.now)
    
    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = self.start_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if self.end_date and self.end_date < self.start_date:
            self.start_date = self.end_date

    def generate_partner_account_status_report(self):
        #data = {'date_start': self.start_date, 'date_stop': self.end_date, 'partner_id': self.partner_id}
        print('generate_partner_account_status_report-self: ', self)
        print('generate_partner_account_status_report-partner_id: ', self.partner_id)
        print('generate_partner_account_status_report-start_date: ', self.start_date)
        print('generate_partner_account_status_report-end_date: ', self.end_date)
        company = []
        by_currency = []
        by_currency_moves = {}
        by_currency_moves_acumulated = {}
        try:
            comp = (self.company_id) if (len(self.company_id) > 0) else self.env.company
            company.append({
                'name': comp.name,
                'company_registry': comp.company_registry,
                'vat': (comp.l10n_latam_identification_type_id.l10n_ve_code if ('l10n_latam_identification_type_id' in comp and len(comp.l10n_latam_identification_type_id) > 0) else '') + comp.vat,
                'logo': comp.logo,
                'phone': comp.phone,
                'mobile': comp.mobile,
                'email': comp.email,
                'website': comp.website,
                'country_id': ((comp.state_id.name + ', ') if (len(comp.state_id) > 0) else '') + comp.country_id.name,
                'font': comp.font,
                'company_details': comp.company_details,
                'primary_color': 'height: 25px; background-color: ' + (comp.primary_color if (comp.primary_color != False) else '#808080') + '; margin-top: 0px; text-align: center;',
                'secondary_color': 'height: 25px; background-color: ' + (comp.secondary_color if (comp.secondary_color != False) else '#808080') + '; margin-top: 0px; text-align: center;',
            })
            now = datetime.now()
            params = []
            params.append(self.partner_id.id)
            params.append(self.company_id.id)
            params.append(('line_section', 'line_note'))
            params.append('asset_receivable')
            params.append('posted')
            params.append(self.start_date.strftime("%Y-%m-%d"))
            self._cr.execute("""
                                    SELECT aml.currency_id, rc.name, sum(amount_currency) FROM account_move_line aml INNER JOIN account_account aa ON aml.account_id=aa.id
                                     INNER JOIN res_currency rc ON aml.currency_id=rc.id
                                     where aml.partner_id = %s AND aml.company_id = %s AND aml.display_type not in %s AND aa.account_type = %s
                                     AND aml.parent_state = %s AND aml.date < %s GROUP BY aml.currency_id, rc.name ORDER BY aml.currency_id
                                """, params)
            receivable_id = self._cr.fetchall()
            print('generate_partner_account_status_report-receivable_id: ', receivable_id)
            balance_initial = 0.0
            for rec in receivable_id:
                balance_initial = rec[2]
                if (rec[1] not in by_currency_moves):
                    by_currency_moves[rec[1]] = []
                    by_currency_moves_acumulated[rec[1]] = {}
                    by_currency.append({ 'currency_id': rec[0], 'currency_name': rec[1] })
                    by_currency_moves[rec[1]].append({
                        'move_id': 0,
                        'currency_id': rec[0],
                        'currency_name': rec[1],
                        'date': str(self.start_date),
                        'line_name': 'Balance inicial',
                        'move_type': '',
                        'debit': '',
                        'credit': '',
                        'balance': str("{0:.2f}".format(round(balance_initial, 2))).replace('.',','),
                    })
                    if ('balance' not in by_currency_moves_acumulated[rec[1]]):
                        by_currency_moves_acumulated[rec[1]]['balance'] = round(balance_initial, 2)

            move_line_ids = self.env['account.move.line'].search([('partner_id', '=', self.partner_id.id),
                #('move_id.move_type','in',['out_invoice','out_receipt', 'entry']),
                ('company_id', '=', self.company_id.id),
                ('display_type', 'not in', ['line_section', 'line_note']),
                ('account_id.account_type','in', ['asset_receivable', 'liability_payable']),
                ('parent_state', '=', 'posted'),
                ('date','<=', self.end_date.strftime("%Y-%m-%d")),
                ('date','>=', self.start_date.strftime("%Y-%m-%d"))], order="currency_id, date, id")
            #print('generate_partner_account_status_report-move_line_ids: ', move_line_ids)
            for line_id in move_line_ids:
                if (line_id.currency_id.name not in by_currency_moves):
                    by_currency_moves[line_id.currency_id.name] = []
                    by_currency_moves_acumulated[line_id.currency_id.name] = {}
                    by_currency.append({ 'currency_id': line_id.currency_id.id, 'currency_name': line_id.currency_id.name })
                    balance_initial = 0.0
                    for rec in receivable_id:
                        if (rec[0] == line_id.currency_id.id):
                            balance_initial = rec[2]

                    by_currency_moves[line_id.currency_id.name].append({
                        'move_id': 0,
                        'currency_id': line_id.currency_id.id,
                        'currency_name': line_id.currency_id.name,
                        'date': str(self.start_date),
                        'line_name': 'Balance inicial',
                        'move_type': '',
                        'debit': '',
                        'credit': '',
                        'balance': str("{0:.2f}".format(round(balance_initial, 2))).replace('.',','),
                    })
                    if ('balance' not in by_currency_moves_acumulated[line_id.currency_id.name]):
                        by_currency_moves_acumulated[line_id.currency_id.name]['balance'] = round(balance_initial, 2)
                        #print('generate_partner_account_status_report-by_currency_moves-if: ', by_currency_moves_acumulated[move_id.currency_id.name])

                if (line_id.debit != 0.0):
                    by_currency_moves_acumulated[line_id.currency_id.name]['balance'] = by_currency_moves_acumulated[line_id.currency_id.name]['balance'] + (line_id.debit/(line_id.debit/line_id.amount_currency))
                else:
                    by_currency_moves_acumulated[line_id.currency_id.name]['balance'] = by_currency_moves_acumulated[line_id.currency_id.name]['balance'] + (line_id.credit/(line_id.credit/line_id.amount_currency))

                by_currency_moves[line_id.currency_id.name].append({
                    'move_id': line_id.id,
                    'currency_id': line_id.currency_id.id,
                    'currency_name': line_id.currency_id.name,
                    'date': str(line_id.date),
                    'line_name': (line_id.name if (line_id.move_type != 'entry') else line_id.ref),
                    'move_type': 'Factura' if (line_id.move_type == 'out_invoice') else ('Nota de crédito' if (line_id.move_type == 'out_refund') else 'Recibo'),
                    'debit': str("{0:.2f}".format(round(((line_id.debit/(line_id.debit/line_id.amount_currency)) if (line_id.debit != 0.0) else line_id.debit), 2))).replace('.',','),
                    'credit': str("{0:.2f}".format(round(((line_id.credit/(line_id.credit/line_id.amount_currency)) if (line_id.credit != 0.0) else line_id.credit), 2))).replace('.',','),
                    'balance': str("{0:.2f}".format(round(by_currency_moves_acumulated[line_id.currency_id.name]['balance'], 2))).replace('.',','),
                })

                #print('generate_partner_account_status_report-by_currency_moves-for: ', by_currency_moves[move_id.currency_id.name])
                #print('generate_partner_account_status_report-by_currency_moves_acumulated-for: ', by_currency_moves_acumulated[move_id.currency_id.name])

            #print('generate_partner_account_status_report-by_currency: ', by_currency)
            #print('generate_partner_account_status_report-by_currency_moves: ', by_currency_moves)
            #print('generate_partner_account_status_report-by_currency_moves_acumulated(r): ', by_currency_moves_acumulated)
            for by_cur in by_currency:
                by_currency_moves[by_cur['currency_name']].append({
                    'move_id': 0,
                    'currency_id': 0,
                    'currency_name': by_cur['currency_name'],
                    'date': str(self.end_date),
                    'line_name': 'Saldo final',
                    'move_type': '',
                    'debit': '',
                    'credit': '',
                    'balance': str("{0:.2f}".format(by_currency_moves_acumulated[by_cur['currency_name']]['balance'])).replace('.',','),
                })

            data = {
                'id': self.id,
                'model': self._name,
                'date': datetime.now(),
                'start_date': self.start_date,
                'end_date': self.end_date,
                'partner_name': self.partner_id.name,
                'company': company,
                'by_currency': by_currency,
                'by_currency_moves': by_currency_moves,
                'by_currency_moves_acumulated': by_currency_moves_acumulated,
                'name': 'Estado_de_cuenta' + '_' + self.partner_id.name.replace(' ', '_'),
            }
            #print('generate_partner_account_status_report-data: ', data)
            return self.env.ref(
                'partner_report_currency.action_partner_account_status'
            ).report_action(self, data=data)
        except:
            raise UserError(
                "Disculpe Hubo un Error al Intenter Imprimir el Reporte" +
                "Intentelo de Nuevo, y si el Problema persiste, " +
                "Contacte a su Proveedor de Servicios."
            )