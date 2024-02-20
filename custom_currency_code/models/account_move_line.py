# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields
from datetime import datetime, timedelta
from odoo.tools.misc import format_date
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    currency_code = fields.Char(string='Código de la moneda', compute="_compute_currency_code")
    account_id_code = fields.Char(string='Codigo de la cuenta', related='account_id.code')
    account_id_name = fields.Char(string='Nombre de la cuenta', related='account_id.name')
    custom_currency_rate = fields.Monetary(string='Tasa de cambio', compute='_compute_currency_code', currency_field='company_currency_id')
    debit_currency = fields.Monetary(string='Importe en Debito', compute='_compute_currency_code', currency_field='currency_id')
    credit_currency = fields.Monetary(string='Importe en Credito', compute='_compute_currency_code', currency_field='currency_id')

    @api.depends('currency_id')
    def _compute_currency_code(self):
        #_logger.warning('_compute_currency_code-self: %s', self)
        for aml in self:
            #_logger.warning('_compute_currency_code-aml: %s', aml)
            aml.currency_code = (aml.currency_id.code if (len(aml.currency_id) > 0) else self.env.company.currency_id.code)
            if (aml.company_currency_id != aml.currency_id):
                if (aml.debit != 0.0 and aml.amount_currency != 0.0):
                    aml.custom_currency_rate = round((aml.debit / aml.amount_currency), 2)
                if (aml.debit != 0.0):
                    aml.debit_currency = (aml.amount_currency if (aml.amount_currency > 0) else (aml.amount_currency * (-1)))
                    aml.credit_currency = 0.0
                if (aml.credit != 0.0 and aml.amount_currency != 0.0):
                    aml.custom_currency_rate = round((aml.credit / aml.amount_currency), 2)
                if (aml.credit != 0.0):
                    aml.credit_currency = (aml.amount_currency if (aml.amount_currency > 0) else (aml.amount_currency * (-1)))
                    aml.debit_currency = 0.0
                if (aml.custom_currency_rate == False):
                    aml.custom_currency_rate = 0.0
                if (aml.custom_currency_rate < 0.0):
                    aml.custom_currency_rate = aml.custom_currency_rate * (-1)
            else:
                aml.custom_currency_rate = 0.0
                aml.debit_currency = 0.0
                aml.credit_currency = 0.0