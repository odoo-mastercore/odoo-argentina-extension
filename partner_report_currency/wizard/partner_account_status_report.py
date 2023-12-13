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
        #_logger.info('generate_partner_account_status_report-self: %s', self)
        #_logger.info('generate_partner_account_status_report-partner_id: %s', self.partner_id)
        #_logger.info('generate_partner_account_status_report-start_date: %s', self.start_date)
        #_logger.info('generate_partner_account_status_report-end_date: %s', self.end_date)
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
            params.append(('out_invoice', 'out_refund', 'out_receipt', 'in_invoice', 'in_receipt', 'in_refund'))
            #params.append(('line_section', 'line_note'))
            #params.append('asset_receivable')
            params.append('posted')
            params.append(self.start_date.strftime("%Y-%m-%d"))
            #_logger.info('generate_partner_account_status_report-params: %s', params)
            '''self._cr.execute("""
                                    SELECT aml.currency_id, rc.name, sum(amount_currency) FROM account_move_line aml INNER JOIN account_account aa ON aml.account_id=aa.id
                                     INNER JOIN res_currency rc ON aml.currency_id=rc.id
                                     where aml.partner_id = %s AND aml.company_id = %s AND aml.display_type not in %s AND aa.account_type = %s
                                     AND aml.parent_state = %s AND aml.date < %s GROUP BY aml.currency_id, rc.name ORDER BY aml.currency_id
                                """, params)'''
            self._cr.execute("""
                                    SELECT am.currency_id, rc.name, sum(CASE WHEN (am.move_type = 'out_refund' OR am.move_type = 'in_refund') THEN (am.amount_residual * (-1)) ELSE (am.amount_residual) END) FROM account_move am INNER JOIN res_currency rc
                                    ON am.currency_id = rc.id WHERE am.partner_id = %s AND am.company_id = %s AND am.move_type IN %s
                                     AND am.state = %s AND am.invoice_date < %s GROUP BY am.currency_id, rc.name ORDER BY am.currency_id
                                """, params)
            receivable_id = self._cr.fetchall()
            #_logger.info('generate_partner_account_status_report-receivable_id: %s', receivable_id)
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
                ('date','>=', self.start_date.strftime("%Y-%m-%d"))], order="date asc, id asc")
            #_logger.info('generate_partner_account_status_report-move_line_ids: %s', move_line_ids)
            for line_id in move_line_ids:
                #_logger.info('generate_partner_account_status_report-line_id: %s', line_id)
                #_logger.info('generate_partner_account_status_report-date: %s', line_id.date)
                #_logger.info('generate_partner_account_status_report-move_id: %s', line_id.move_id)
                #_logger.info('generate_partner_account_status_report-reconciled_invoice_ids: %s', line_id.payment_id.reconciled_invoice_ids if line_id.payment_id != False else 'N/A')
                #_logger.info('generate_partner_account_status_report-reconciled_bill_ids: %s', line_id.payment_id.reconciled_bill_ids if line_id.payment_id != False else 'N/A')
                #_logger.info('generate_partner_account_status_report-payment_id: %s', line_id.payment_id)
                #_logger.info('generate_partner_account_status_report-payment_group_id: %s', line_id.payment_id.payment_group_id)
                #_logger.info('generate_partner_account_status_report-selected_debt_currency_id: %s', line_id.payment_id.payment_group_id.selected_debt_currency_id)
                if (line_id.move_type == 'entry'):
                    if (line_id.amount_residual != 0.0):
                        currency_group = line_id.currency_id.name
                    else:
                        currency_group = (line_id.payment_id.payment_group_id.selected_debt_currency_id.name if (len(line_id.payment_id.payment_group_id.selected_debt_currency_id) > 0) else self.company_id.currency_id.name)
                else:
                    currency_group = line_id.currency_id.name
                #_logger.info('generate_partner_account_status_report-currency_group: %s', currency_group)
                if (currency_group not in by_currency_moves):
                    by_currency_moves[currency_group] = []
                    by_currency_moves_acumulated[currency_group] = {}
                    by_currency.append({ 'currency_id': line_id.currency_id.id, 'currency_name': currency_group })
                    balance_initial = 0.0
                    for rec in receivable_id:
                        if (rec[0] == line_id.currency_id.id):
                            balance_initial = rec[2]

                    by_currency_moves[currency_group].append({
                        'move_id': 0,
                        'currency_id': line_id.currency_id.id,
                        'currency_name': currency_group,
                        'date': str(self.start_date),
                        'line_name': 'Balance inicial',
                        'move_type': '',
                        'debit': '',
                        'credit': '',
                        'balance': str("{0:.2f}".format(round(balance_initial, 2))).replace('.',','),
                    })
                    if ('balance' not in by_currency_moves_acumulated[currency_group]):
                        by_currency_moves_acumulated[currency_group]['balance'] = round(balance_initial, 2)

                #_logger.info('line_id.line_id.currency_id.name %s', line_id.currency_id.name)
                if (currency_group == line_id.currency_id.name):
                    if ((line_id.amount_currency != 0.0) or (self.company_id.currency_id.name == currency_group)):
                        if (line_id.debit != 0.0):
                            rate = (line_id.debit/line_id.amount_currency)
                        else:
                            rate = (line_id.credit/line_id.amount_currency)
                    else:
                        c_rate = self.env['res.currency.rate'].search([('company_id', '=', self.company_id.id), ('name', '<=', str(line_id.date)), ('currency_id', '=', line_id.currency_id.id)], order='name desc', limit=1)
                        if (len(c_rate) > 0):
                            rate = (1/c_rate.rate)
                        else:
                            rate = 1
                else:
                    if (('aux_inverse_currency_rate' in line_id) and (line_id.aux_inverse_currency_rate != False) and (line_id.aux_inverse_currency_rate > 1)):
                        rate = line_id.aux_inverse_currency_rate
                    elif ((len(line_id.payment_id.reconciled_invoice_ids) > 0) and ('l10n_ar_currency_rate' in line_id.payment_id.reconciled_invoice_ids[0]) and (line_id.payment_id.reconciled_invoice_ids[0].l10n_ar_currency_rate > 1)):
                        rate = line_id.payment_id.reconciled_invoice_ids[0].l10n_ar_currency_rate
                    else:
                        c_rate = self.env['res.currency.rate'].search([('company_id', '=', self.company_id.id), ('name', '<=', str(line_id.date)), ('currency_id.name', '=', currency_group)], order='name desc', limit=1)
                        if (len(c_rate) > 0):
                            rate = (1/c_rate.rate)
                        else:
                            rate = 1
                    if (line_id.amount_currency < 0):
                        rate = rate * (-1)
                #_logger.info('line_id.rate %s', rate)

                if (line_id.debit != 0.0):
                    by_currency_moves_acumulated[currency_group]['balance'] = by_currency_moves_acumulated[currency_group]['balance'] + (line_id.debit/rate)
                else:
                    by_currency_moves_acumulated[currency_group]['balance'] = by_currency_moves_acumulated[currency_group]['balance'] + (line_id.credit/rate)

                by_currency_moves[currency_group].append({
                    'move_id': line_id.id,
                    'currency_id': line_id.currency_id.id,
                    'currency_name': currency_group,
                    'date': str(line_id.date),
                    'line_name': line_id.move_id.name if (line_id.move_type == 'out_invoice' or line_id.move_type == 'in_invoice') else line_id.name, #(line_id.name if (line_id.move_type != 'entry') else line_id.ref),
                    'move_type': 'Factura' if (line_id.move_type == 'out_invoice' or line_id.move_type == 'in_invoice') else ('Nota de crédito' if (line_id.move_type == 'out_refund' or line_id.move_type == 'in_refund') else 'Recibo'),
                    'debit': str("{0:.2f}".format(round(((line_id.debit/rate) if (line_id.debit != 0.0) else line_id.debit), 2))).replace('.',','),
                    'credit': str("{0:.2f}".format(round(((line_id.credit/rate) if (line_id.credit != 0.0) else line_id.credit), 2))).replace('.',','),
                    'balance': str("{0:.2f}".format(round(by_currency_moves_acumulated[currency_group]['balance'], 2))).replace('.',','),
                })

            #_logger.info('generate_partner_account_status_report-by_currency: %s', by_currency)
            #_logger.info('generate_partner_account_status_report-by_currency_moves: %s', by_currency_moves)
            #_logger.info('generate_partner_account_status_report-by_currency_moves_acumulated(r): %s', by_currency_moves_acumulated)
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
                'partner_type': 'Cliente: ' if (self.partner_id.customer_rank >= self.partner_id.supplier_rank) else 'Proveedor: ',
                'company': company,
                'by_currency': by_currency,
                'by_currency_moves': by_currency_moves,
                'by_currency_moves_acumulated': by_currency_moves_acumulated,
                'name': 'Estado_de_cuenta' + '_' + self.partner_id.name.replace(' ', '_'),
            }
            #_logger.info('generate_partner_account_status_report-data: %s', data)
            return self.env.ref(
                'partner_report_currency.action_partner_account_status'
            ).report_action(self, data=data)
        except:
            raise UserError(
                "Disculpe Hubo un Error al Intenter Imprimir el Reporte" +
                "Intentelo de Nuevo, y si el Problema persiste, " +
                "Contacte a su Proveedor de Servicios."
            )