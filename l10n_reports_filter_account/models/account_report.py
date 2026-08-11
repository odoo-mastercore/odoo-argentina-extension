# -*- coding: utf-8 -*-
################################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
################################################################################

from odoo import models, api, _, fields
from datetime import datetime, timedelta
from odoo.tools.misc import format_date
from odoo.tools import SQL, Query
import logging
_logger = logging.getLogger(__name__)

class AccountReport(models.AbstractModel):
    _inherit = "account.report"

    filter_account_acc = True
    filter_exclude_zero_balance = fields.Selection(
        string="Excluir balances en 0",
        selection=[ ('by_default', "Activado por defecto"), ('optional', "Opcional"),('never', "Nunca"), ],compute=lambda report: report._compute_report_option_filter( 'filter_exclude_zero_balance','never', ),readonly=False,store=True,depends=['root_report_id', 'section_main_report_ids'],)

    @api.readonly
    def get_options(self, previous_options):
        res = super(AccountReport, self).get_options(previous_options)
        if self.filter_account_acc:
            if ('allowed_company_ids' in self._context):
                account_accounts = self.env['account.account'].search([('company_ids', 'in', self._context.get('allowed_company_ids')), ('account_type', 'in', ['asset_receivable', 'liability_payable'])])
            else:
                account_accounts = self.env['account.account'].search([('account_type', 'in', ['asset_receivable', 'liability_payable'])])
            #_logger.warning('ReportPartnerLedger-_get_options-account_accounts: %s', account_accounts)
            res['account_accounts'] = [{'id': aa.id, 'name': (aa.code +' - ' + aa.name), 'selected': False} for aa in account_accounts]
            if 'account_acc' in self._context:
                for c in res['account_accounts']:
                    if c['id'] == self._context.get('account_acc'):
                        c['selected'] = True
            res['account_accts'] = True
        if (previous_options == False or 'account_account_ids' not in previous_options):
            res['account_account_ids'] = []
            res['account_acc_ids'] = []
        if (previous_options == False or 'exclude_companies_without_difference' not in previous_options):
            res['exclude_companies_without_difference'] = False
        else:
            res['account_account_ids'] = previous_options['account_account_ids']
            res['account_acc_ids'] = previous_options['account_acc_ids']
            res['exclude_companies_without_difference'] = previous_options['exclude_companies_without_difference'] if ('exclude_companies_without_difference' in previous_options) else False
        return res
    
    @api.model
    def _currency_table_aml_join_for_leader_partner(self, options, aml_alias=SQL('account_move_line')) -> SQL:
        """ Returns the JOIN condition to the currency table in a query needing to use it to convert aml balances from one currency to another.
        """
        account_acc_ids = []
        if ('account_acc_ids' in options and len(options['account_acc_ids']) > 0):
            account_acc_ids = options['account_acc_ids']
        if ('account_acc_ids' in self._context and len(self._context.get('account_acc_ids')) > 0):
            account_acc_ids = self._context.get('account_acc_ids')
        if options['currency_table']['type'] == 'cta':
            return SQL(
                """
                    JOIN account_account aml_ct_account
                        ON aml_ct_account.id = %(aml_table)s.account_id
                    LEFT JOIN %(currency_table)s
                        ON %(aml_table)s.company_id = account_currency_table.company_id
                        AND (
                            account_currency_table.rate_type = CASE
                                WHEN aml_ct_account.account_type LIKE %(equity_prefix)s THEN 'historical'
                                WHEN aml_ct_account.account_type LIKE ANY (ARRAY[%(income_prefix)s, %(expense_prefix)s, 'equity_unaffected']) THEN 'average'
                                ELSE 'closing'
                            END
                        )
                        AND (account_currency_table.date_from IS NULL OR account_currency_table.date_from <= %(aml_table)s.date)
                        AND (account_currency_table.date_next IS NULL OR account_currency_table.date_next > %(aml_table)s.date)
                        AND (account_currency_table.period_key = %(period_key)s OR account_currency_table.period_key IS NULL)
                        AND (account_account acc_acc ON account_move_line.account_id = acc_acc.id)
                """,
                aml_table=aml_alias,
                equity_prefix='equity%',
                income_prefix='income%',
                expense_prefix='expense%',
                currency_table=self._get_currency_table(options),
                period_key=options['date']['currency_table_period_key'],
            )

        return SQL(
            """
                JOIN %(currency_table)s
                    ON %(aml_table)s.company_id = account_currency_table.company_id
                    AND (account_currency_table.period_key = %(period_key)s OR account_currency_table.period_key IS NULL)
            """,
            aml_table=aml_alias,
            currency_table=self._get_currency_table(options),
            period_key=options['date']['currency_table_period_key'],
        )

    def _init_options_exclude_zero_balance(self, options, previous_options):
        if self.filter_exclude_zero_balance != 'never':
            previous_value = previous_options.get('exclude_zero_balance')

            if previous_value is not None:
                options['exclude_zero_balance'] = previous_value
            else:
                options['exclude_zero_balance'] = (
                    self.filter_exclude_zero_balance == 'by_default'
                )
        else:
            options['exclude_zero_balance'] = False

    def get_report_information(self, options):
        report_information = super().get_report_information(options)

        report_information['filters']['show_exclude_zero_balance'] = (
            self.filter_exclude_zero_balance
        )

        return report_information