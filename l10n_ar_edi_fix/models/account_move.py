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
                        'Importe': float_repr((sign * eval(amount_field)), precision_digits=2)})
        return res if res else None