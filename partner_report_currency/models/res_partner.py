# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields
from datetime import datetime, timedelta
from odoo.tools.misc import format_date
from odoo.exceptions import UserError, ValidationError

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter
import io

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    def _get_report_base_filename(self):
        return 'Pagos_pendientes' + '_' + self.name.replace(' ', '_')

    def show_partner_pending_payments(self):
        #print('show_partner_pending_payments-self: ', self)
        company = []
        by_currency = []
        by_currency_pay = []
        by_currency_moves = {}
        by_payment_unmatched = {}
        by_currency_moves_acumulated = {}
        by_payment_unmatched_acumulated = {}
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
            move_ids = self.env['account.move'].search([('partner_id', '=', self.id),
                ('move_type','in',['out_invoice','out_receipt', 'out_refund', 'in_invoice', 'in_receipt', 'in_refund']),
                ('state', '=', 'posted'),
                ('payment_state', '!=','paid')], order="company_id, currency_id, invoice_date")
            #print('show_partner_pending_payments-move_ids: ', move_ids)
            for move_id in move_ids:
                if (('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name) not in by_currency_moves):
                    by_currency_moves[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)] = []
                    by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)] = {}
                    by_currency.append({ 'company_id': move_id.company_id.id, 'key': ('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name), 'company_name': move_id.company_id.name, 'currency_name': move_id.currency_id.name, 'currency_symbol': move_id.currency_id.symbol, 'currency_position': move_id.currency_id.position })

                by_currency_moves[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)].append({
                    'move_id': move_id.id,
                    'currency_id': move_id.currency_id.id,
                    'currency_name': move_id.currency_id.name,
                    'invoice_date': str(move_id.invoice_date),
                    'invoice_date_due': str(move_id.invoice_date_due),
                    'name': move_id.name,
                    'move_type': 'Factura' if (move_id.move_type == 'out_invoice' or move_id.move_type == 'in_invoice') else ('Nota de crédito' if (move_id.move_type == 'out_refund' or move_id.move_type == 'in_refund') else 'Recibo'),
                    'amount_total': move_id.currency_id.name + ' ' + str("{0:.2f}".format(round(move_id.amount_total, 2))).replace('.',','), #((move_id.currency_id.symbol + ' ') if (move_id.currency_id.position == 'before') else '') + str(round(move_id.amount_total, 2)) + ((' ' + move_id.currency_id.symbol) if (move_id.currency_id.position == 'after') else ''),
                    'amount_residual': move_id.currency_id.name + ' ' + str("{0:.2f}".format(round(move_id.amount_residual, 2))).replace('.',','), #((move_id.currency_id.symbol + ' ') if (move_id.currency_id.position == 'before') else '') + str(round(move_id.amount_residual, 2)) + ((' ' + move_id.currency_id.symbol) if (move_id.currency_id.position == 'after') else ''),
                    'amount_payment': move_id.currency_id.name + ' ' + str("{0:.2f}".format(round((move_id.amount_total - move_id.amount_residual), 2))).replace('.',','), #((move_id.currency_id.symbol + ' ') if (move_id.currency_id.position == 'before') else '') + str(round((move_id.amount_total - move_id.amount_residual), 2)) + ((' ' + move_id.currency_id.symbol) if (move_id.currency_id.position == 'after') else ''),
                })

                #print('show_partner_pending_payments-by_currency_moves_acumulated(p): ', by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)])
                #print('show_partner_pending_payments-currency_id.name in: ', ('amount_total' not in by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)]))
                if ('amount_total' not in by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)]):
                    by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)]['amount_total'] = move_id.amount_total
                    by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)]['amount_residual'] = move_id.amount_residual
                    by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)]['amount_payment'] = round((move_id.amount_total - move_id.amount_residual), 2)
                    #print('show_partner_pending_payments-by_currency_moves-if: ', by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)])
                else:
                    #print('show_partner_pending_payments-by_currency_moves-else: ', by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)])
                    by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)]['amount_total'] = by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)]['amount_total'] + move_id.amount_total
                    by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)]['amount_residual'] = by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)]['amount_residual'] + move_id.amount_residual
                    by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)]['amount_payment'] = by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)]['amount_payment'] + round((move_id.amount_total - move_id.amount_residual), 2)

                #print('show_partner_pending_payments-by_currency_moves-for: ', by_currency_moves[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)])
                #print('show_partner_pending_payments-by_currency_moves_acumulated-for: ', by_currency_moves_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)])

            #print('show_partner_pending_payments-by_currency: ', by_currency)
            #print('show_partner_pending_payments-by_currency_moves: ', by_currency_moves)
            for by_cur in by_currency:
                by_currency_moves_acumulated[by_cur['key']]['amount_total'] = by_cur['currency_name'] + ' ' + str("{0:.2f}".format(by_currency_moves_acumulated[by_cur['key']]['amount_total'])).replace('.',',') #((by_cur['currency_symbol'] + ' ') if (by_cur['currency_position'] == 'before') else '') + str(round(by_currency_moves_acumulated[by_cur['key']]['amount_total'], 2)) + ((' ' + by_cur['currency_symbol']) if (by_cur['currency_position'] == 'after') else '')
                by_currency_moves_acumulated[by_cur['key']]['amount_residual'] = by_cur['currency_name'] + ' ' + str("{0:.2f}".format(by_currency_moves_acumulated[by_cur['key']]['amount_residual'])).replace('.',',') #((by_cur['currency_symbol'] + ' ') if (by_cur['currency_position'] == 'before') else '') + str(round(by_currency_moves_acumulated[by_cur['key']]['amount_residual'], 2)) + ((' ' + by_cur['currency_symbol']) if (by_cur['currency_position'] == 'after') else '')
                by_currency_moves_acumulated[by_cur['key']]['amount_payment'] = by_cur['currency_name'] + ' ' + str("{0:.2f}".format(by_currency_moves_acumulated[by_cur['key']]['amount_payment'])).replace('.',',') #((by_cur['currency_symbol'] + ' ') if (by_cur['currency_position'] == 'before') else '') + str(round(by_currency_moves_acumulated[by_cur['key']]['amount_payment'], 2)) + ((' ' + by_cur['currency_symbol']) if (by_cur['currency_position'] == 'after') else '')

            payment_unmatched = self.env['account.payment'].search([('partner_id', '=', self.id), ('is_reconciled','=', False), ('state', '=', 'posted')], order="company_id, currency_id, date")

            for payment_id in payment_unmatched:
                if (('c' + str(payment_id.company_id.id) + '_' + payment_id.currency_id.name) not in by_payment_unmatched):
                    by_payment_unmatched[('c' + str(payment_id.company_id.id) + '_' + payment_id.currency_id.name)]= []
                    by_payment_unmatched_acumulated[('c' + str(payment_id.company_id.id) + '_' + payment_id.currency_id.name)]= {}
                    by_currency_pay.append({  'company_id': payment_id.company_id.id, 'key': ('c' + str(payment_id.company_id.id) + '_' + payment_id.currency_id.name), 'company_name': payment_id.company_id.name, 'currency_name': payment_id.currency_id.name, 'currency_symbol': payment_id.currency_id.symbol, 'currency_position': payment_id.currency_id.position })

                by_payment_unmatched[('c' + str(payment_id.company_id.id) + '_' + payment_id.currency_id.name)].append({
                    'payment_id': payment_id.id,
                    'company_id': payment_id.company_id.id,
                    'company_name': payment_id.company_id.name,
                    'name': payment_id.name,
                    'date': str(payment_id.date),
                    'currency_id': payment_id.currency_id.id,
                    'currency_name': payment_id.currency_id.name,
                    'journal_id': payment_id.journal_id.name,
                    'payment_type': 'Enviar' if (payment_id.payment_type == 'outbound') else 'Recibir',
                    'amount': payment_id.currency_id.name + ' ' + str("{0:.2f}".format(round(payment_id.amount, 2))).replace('.',','),
                    'amount_company_currency': payment_id.company_id.currency_id.name + ' ' + str("{0:.2f}".format(round(payment_id.amount_company_currency, 2))).replace('.',','),
                    'ref': payment_id.ref,
                })

                #print('show_partner_pending_payments-by_payment_unmatched_acumulated(p): ', by_payment_unmatched_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)])
                #print('show_partner_pending_payments-currency_id.name in: ', ('amount_total' not in by_payment_unmatched_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)]))
                if ('amount' not in by_payment_unmatched_acumulated[('c' + str(payment_id.company_id.id) + '_' + payment_id.currency_id.name)]):
                    by_payment_unmatched_acumulated[('c' + str(payment_id.company_id.id) + '_' + payment_id.currency_id.name)]['amount'] = payment_id.amount
                    by_payment_unmatched_acumulated[('c' + str(payment_id.company_id.id) + '_' + payment_id.currency_id.name)]['amount_company_currency'] = payment_id.amount_company_currency
                    #print('show_partner_pending_payments-by_payment_unmatched-if: ', by_payment_unmatched_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)])
                else:
                    #print('show_partner_pending_payments-by_payment_unmatched-else: ', by_payment_unmatched_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)])
                    by_payment_unmatched_acumulated[('c' + str(payment_id.company_id.id) + '_' + payment_id.currency_id.name)]['amount'] = by_payment_unmatched_acumulated[('c' + str(payment_id.company_id.id) + '_' + payment_id.currency_id.name)]['amount'] + payment_id.amount
                    by_payment_unmatched_acumulated[('c' + str(payment_id.company_id.id) + '_' + payment_id.currency_id.name)]['amount_company_currency'] = by_payment_unmatched_acumulated[('c' + str(payment_id.company_id.id) + '_' + payment_id.currency_id.name)]['amount_company_currency'] + payment_id.amount_company_currency

                #print('show_partner_pending_payments-by_payment_unmatched-for: ', by_payment_unmatched[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)])
                #print('show_partner_pending_payments-by_payment_unmatched_acumulated-for: ', by_payment_unmatched_acumulated[('c' + str(move_id.company_id.id) + '_' + move_id.currency_id.name)])

            #print('show_partner_pending_payments-by_currency: ', by_currency)
            #print('show_partner_pending_payments-by_currency_moves: ', by_currency_moves)
            for by_cur_pay in by_currency_pay:
                by_payment_unmatched_acumulated[by_cur_pay['key']]['amount'] = by_cur_pay['currency_name'] + ' ' + str("{0:.2f}".format(by_payment_unmatched_acumulated[by_cur_pay['key']]['amount'])).replace('.',',')
                by_payment_unmatched_acumulated[by_cur_pay['key']]['amount_company_currency'] = by_cur_pay['currency_name'] + ' ' + str("{0:.2f}".format(by_payment_unmatched_acumulated[by_cur_pay['key']]['amount_company_currency'])).replace('.',',')

            #print('show_partner_pending_payments-by_currency_moves_acumulated(r): ', by_currency_moves_acumulated)
            data = {
                'id': self.id,
                'model': self._name,
                'date': datetime.now(),
                'partner_name': self.name,
                'partner_type': 'Cliente: ' if (self.customer_rank >= self.supplier_rank) else 'Proveedor: ',
                'company': company,
                'by_currency': by_currency,
                'by_currency_moves': by_currency_moves,
                'by_currency_moves_acumulated': by_currency_moves_acumulated,
                'payment_unmatched': True if (len(by_currency_pay) > 0) else False,
                'by_currency_pay': by_currency_pay,
                'by_payment_unmatched': by_payment_unmatched,
                'by_payment_unmatched_acumulated': by_payment_unmatched_acumulated,
                'name': 'Pagos_pendientes' + '_' + self.name.replace(' ', '_'),
            }
            #print('show_partner_pending_payments-data: ', data)
            return self.env.ref(
                'partner_report_currency.action_partner_pending_payments'
            ).report_action(self, data=data)
        except:
            raise UserError(
                "Disculpe Hubo un Error al Intenter Imprimir el Reporte" +
                "Intentelo de Nuevo, y si el Problema persiste, " +
                "Contacte a su Proveedor de Servicios."
            )

    def show_partner_account_status_report(self):
        comp = (self.company_id) if (len(self.company_id) > 0) else self.env.company
        return {
            'name': _('Informe de Estado de cuenta'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'partner.account.status.report',
            'target': 'new',
            'context': { 'default_partner_id': self.id, 'default_company_id': comp.id }
        }