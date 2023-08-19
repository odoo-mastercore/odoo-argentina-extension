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
        by_currency_moves = {}
        by_currency_moves_acumulated = {}
        #try:
        comp = (self.company_id) if (len(self.company_id) > 0) else self.env.company
        company.append({
            'name': comp.name,
            'company_registry': comp.company_registry,
            'vat': (comp.l10n_latam_identification_type_id.l10n_ve_code if (len(comp.l10n_latam_identification_type_id) > 0) else '') + comp.vat,
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
            ('move_type','in',['out_invoice','out_receipt']),
            ('state', '=', 'posted'),
            ('payment_state', '!=','paid')], order="currency_id, invoice_date")
        #print('show_partner_pending_payments-move_ids: ', move_ids)
        for move_id in move_ids:
            if (move_id.currency_id.name not in by_currency_moves):
                by_currency_moves[move_id.currency_id.name] = []
                by_currency_moves_acumulated[move_id.currency_id.name] = {}
                by_currency.append({ 'currency_name': move_id.currency_id.name, 'currency_symbol': move_id.currency_id.symbol, 'currency_position': move_id.currency_id.position })

            by_currency_moves[move_id.currency_id.name].append({
                'move_id': move_id.id,
                'currency_id': move_id.currency_id.id,
                'currency_name': move_id.currency_id.name,
                'invoice_date': str(move_id.invoice_date),
                'invoice_date_due': str(move_id.invoice_date_due),
                'name': move_id.name,
                'move_type': 'Factura' if (move_id.move_type == 'out_invoice') else 'Recibo',
                'amount_total': move_id.currency_id.name + ' ' + str("{0:.2f}".format(round(move_id.amount_total, 2))).replace('.',','), #((move_id.currency_id.symbol + ' ') if (move_id.currency_id.position == 'before') else '') + str(round(move_id.amount_total, 2)) + ((' ' + move_id.currency_id.symbol) if (move_id.currency_id.position == 'after') else ''),
                'amount_residual': move_id.currency_id.name + ' ' + str("{0:.2f}".format(round(move_id.amount_residual, 2))).replace('.',','), #((move_id.currency_id.symbol + ' ') if (move_id.currency_id.position == 'before') else '') + str(round(move_id.amount_residual, 2)) + ((' ' + move_id.currency_id.symbol) if (move_id.currency_id.position == 'after') else ''),
                'amount_payment': move_id.currency_id.name + ' ' + str("{0:.2f}".format(round((move_id.amount_total - move_id.amount_residual), 2))).replace('.',','), #((move_id.currency_id.symbol + ' ') if (move_id.currency_id.position == 'before') else '') + str(round((move_id.amount_total - move_id.amount_residual), 2)) + ((' ' + move_id.currency_id.symbol) if (move_id.currency_id.position == 'after') else ''),
            })

            #print('show_partner_pending_payments-by_currency_moves_acumulated(p): ', by_currency_moves_acumulated[move_id.currency_id.name])
            #print('show_partner_pending_payments-currency_id.name in: ', ('amount_total' not in by_currency_moves_acumulated[move_id.currency_id.name]))
            if ('amount_total' not in by_currency_moves_acumulated[move_id.currency_id.name]):
                by_currency_moves_acumulated[move_id.currency_id.name]['amount_total'] = move_id.amount_total
                by_currency_moves_acumulated[move_id.currency_id.name]['amount_residual'] = move_id.amount_residual
                by_currency_moves_acumulated[move_id.currency_id.name]['amount_payment'] = round((move_id.amount_total - move_id.amount_residual), 2)
                #print('show_partner_pending_payments-by_currency_moves-if: ', by_currency_moves_acumulated[move_id.currency_id.name])
            else:
                #print('show_partner_pending_payments-by_currency_moves-else: ', by_currency_moves_acumulated[move_id.currency_id.name])
                by_currency_moves_acumulated[move_id.currency_id.name]['amount_total'] = by_currency_moves_acumulated[move_id.currency_id.name]['amount_total'] + move_id.amount_total
                by_currency_moves_acumulated[move_id.currency_id.name]['amount_residual'] = by_currency_moves_acumulated[move_id.currency_id.name]['amount_residual'] + move_id.amount_residual
                by_currency_moves_acumulated[move_id.currency_id.name]['amount_payment'] = by_currency_moves_acumulated[move_id.currency_id.name]['amount_payment'] + round((move_id.amount_total - move_id.amount_residual), 2)

            #print('show_partner_pending_payments-by_currency_moves-for: ', by_currency_moves[move_id.currency_id.name])
            #print('show_partner_pending_payments-by_currency_moves_acumulated-for: ', by_currency_moves_acumulated[move_id.currency_id.name])

        #print('show_partner_pending_payments-by_currency: ', by_currency)
        #print('show_partner_pending_payments-by_currency_moves: ', by_currency_moves)
        for by_cur in by_currency:
            by_currency_moves_acumulated[by_cur['currency_name']]['amount_total'] = by_cur['currency_name'] + ' ' + str("{0:.2f}".format(by_currency_moves_acumulated[by_cur['currency_name']]['amount_total'])).replace('.',',') #((by_cur['currency_symbol'] + ' ') if (by_cur['currency_position'] == 'before') else '') + str(round(by_currency_moves_acumulated[by_cur['currency_name']]['amount_total'], 2)) + ((' ' + by_cur['currency_symbol']) if (by_cur['currency_position'] == 'after') else '')
            by_currency_moves_acumulated[by_cur['currency_name']]['amount_residual'] = by_cur['currency_name'] + ' ' + str("{0:.2f}".format(by_currency_moves_acumulated[by_cur['currency_name']]['amount_residual'])).replace('.',',') #((by_cur['currency_symbol'] + ' ') if (by_cur['currency_position'] == 'before') else '') + str(round(by_currency_moves_acumulated[by_cur['currency_name']]['amount_residual'], 2)) + ((' ' + by_cur['currency_symbol']) if (by_cur['currency_position'] == 'after') else '')
            by_currency_moves_acumulated[by_cur['currency_name']]['amount_payment'] = by_cur['currency_name'] + ' ' + str("{0:.2f}".format(by_currency_moves_acumulated[by_cur['currency_name']]['amount_payment'])).replace('.',',') #((by_cur['currency_symbol'] + ' ') if (by_cur['currency_position'] == 'before') else '') + str(round(by_currency_moves_acumulated[by_cur['currency_name']]['amount_payment'], 2)) + ((' ' + by_cur['currency_symbol']) if (by_cur['currency_position'] == 'after') else '')

        #print('show_partner_pending_payments-by_currency_moves_acumulated(r): ', by_currency_moves_acumulated)
        data = {
            'id': self.id,
            'model': self._name,
            'date': datetime.now(),
            'partner_name': self.name,
            'company': company,
            'by_currency': by_currency,
            'by_currency_moves': by_currency_moves,
            'by_currency_moves_acumulated': by_currency_moves_acumulated,
            'name': 'Pagos_pendientes' + '_' + self.name.replace(' ', '_'),
        }
        #print('show_partner_pending_payments-data: ', data)
        return self.env.ref(
            'partner_report_currency.action_partner_pending_payments'
        ).report_action(self, data=data)
        '''except:
            raise UserError(
                "Disculpe Hubo un Error al Intenter Imprimir el Reporte" +
                "Intentelo de Nuevo, y si el Problema persiste, " +
                "Contacte a su Proveedor de Servicios."
            )'''