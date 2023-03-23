# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import UserError, RedirectWarning
from odoo.tools.float_utils import float_repr, float_round
from odoo.tools import html2plaintext, plaintext2html
from datetime import datetime
import re
import logging
import base64
import json


_logger = logging.getLogger(__name__)
WS_DATE_FORMAT = {'wsfe': '%Y%m%d', 'wsfex': '%Y%m%d', 'wsbfe': '%Y%m%d'}


class AccountMove(models.Model):

    _inherit = "account.move"


    def _get_tributes(self):
        """ Applies on wsfe web service """
        res = []
        not_vat_taxes = self.line_ids.filtered(lambda x: x.tax_line_id and x.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code)
        for tribute in not_vat_taxes:
            base_imp = sum(self.invoice_line_ids.filtered(lambda x: x.tax_ids.filtered(
                lambda y: y.tax_group_id.l10n_ar_tribute_afip_code == tribute.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code)).mapped(
                    'price_subtotal'))
            company_currency = self.currency_id.id == self.company_id.currency_id.id
            amount_field = company_currency and 'tribute.balance' or 'tribute.amount_currency'
            sign = -1 if self.is_inbound() else 1
            res.append({'Id': tribute.tax_line_id.tax_group_id.l10n_ar_tribute_afip_code,
                        'Alic': 0,
                        'Desc': tribute.tax_line_id.tax_group_id.name,
                        'BaseImp': float_repr(base_imp, precision_digits=2),
                        'Importe': float_repr((sign * eval('amount_field')), precision_digits=2)})
        return res if res else None

    @api.model
    def wsfe_get_cae_request(self, client=None):
        self.ensure_one()
        partner_id_code = self._get_partner_code_id(self.commercial_partner_id)
        invoice_number = self._l10n_ar_get_document_number_parts(
            self.l10n_latam_document_number, self.l10n_latam_document_type_id.code)['invoice_number']
        amounts = self._l10n_ar_get_amounts()
        due_payment_date = self._due_payment_date()
        service_start, service_end = self._service_dates()

        related_invoices = self._get_related_invoice_data()
        vat_items = self._get_vat()
        for item in vat_items:
            if 'BaseImp' in item and 'Importe' in item:
                item['BaseImp'] = float_repr(item['BaseImp'], precision_digits=2)
                item['Importe'] = float_repr(item['Importe'], precision_digits=2)
        vat = partner_id_code and self.commercial_partner_id._get_id_number_sanitize()

        tributes = self._get_tributes()
        optionals = self._get_optionals_data()

        ArrayOfAlicIva = client.get_type('ns0:ArrayOfAlicIva')
        ArrayOfTributo = client.get_type('ns0:ArrayOfTributo')
        ArrayOfCbteAsoc = client.get_type('ns0:ArrayOfCbteAsoc')
        ArrayOfOpcional = client.get_type('ns0:ArrayOfOpcional')

        res = {'FeCabReq': {
                   'CantReg': 1, 'PtoVta': self.journal_id.l10n_ar_afip_pos_number, 'CbteTipo': self.l10n_latam_document_type_id.code},
               'FeDetReq': [{'FECAEDetRequest': {
                   'Concepto': int(self.l10n_ar_afip_concept),
                   'DocTipo': partner_id_code or 0,
                   'DocNro': vat and int(vat) or 0,
                   'CbteDesde': invoice_number,
                   'CbteHasta': invoice_number,
                   'CbteFch': self.invoice_date.strftime(WS_DATE_FORMAT['wsfe']),

                   'ImpTotal': float_repr(self.amount_total, precision_digits=2),
                   'ImpTotConc': float_repr(amounts['vat_untaxed_base_amount'], precision_digits=2),  # Not Taxed VAT
                   'ImpNeto': float_repr(amounts['vat_taxable_amount'], precision_digits=2),
                   'ImpOpEx': float_repr(amounts['vat_exempt_base_amount'], precision_digits=2),
                   'ImpTrib': float_repr(amounts['not_vat_taxes_amount'], precision_digits=2),
                   'ImpIVA': float_repr(amounts['vat_amount'], precision_digits=2),

                   # Service dates are only informed when AFIP Concept is (2,3)
                   'FchServDesde': service_start.strftime(WS_DATE_FORMAT['wsfe']) if service_start else False,
                   'FchServHasta': service_end.strftime(WS_DATE_FORMAT['wsfe']) if service_end else False,
                   'FchVtoPago': due_payment_date.strftime(WS_DATE_FORMAT['wsfe']) if due_payment_date else False,
                   'MonId': self.currency_id.l10n_ar_afip_code,
                   'MonCotiz':  float_repr(self.l10n_ar_currency_rate, precision_digits=6),
                   'CbtesAsoc': ArrayOfCbteAsoc([related_invoices]) if related_invoices else None,
                   'Iva': ArrayOfAlicIva(vat_items) if vat_items else None,
                   'Tributos': ArrayOfTributo(tributes) if tributes else None,
                   'Opcionales': ArrayOfOpcional(optionals) if optionals else None,
                   'Compradores': None}}]}
        _logger.warning('----------------------------------')
        _logger.warning(res)
        return res
