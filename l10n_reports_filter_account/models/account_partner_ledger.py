# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields
from datetime import datetime, timedelta
from odoo.tools.misc import format_date

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter
import io
import logging
_logger = logging.getLogger(__name__)

class ReportPartnerLedger(models.AbstractModel):
    _inherit = "account.partner.ledger"
    
    filter_account_acc = True

    @api.model
    def _get_options(self, previous_options=None):
        #_logger.warning('ReportPartnerLedger-_get_options-previous_options: %s', previous_options)
        res = super(ReportPartnerLedger, self)._get_options(previous_options)
        #_logger.warning('ReportPartnerLedger-_get_options-res(I): %s', res)
        if self.filter_account_acc :
            if ('allowed_company_ids' in self._context):
                account_accounts = self.env['account.account'].search([('company_id', 'in', self._context.get('allowed_company_ids'))])
            else:
                account_accounts = self.env['account.account'].search([])
            #_logger.warning('ReportPartnerLedger-_get_options-account_accounts: %s', account_accounts)
            res['account_accounts'] = [{'id': aa.id, 'name': aa.name, 'selected': False} for aa in account_accounts]
            if 'account_acc' in self._context:
                for c in res['account_accounts']:
                    if c['id'] == self._context.get('account_acc'):
                        c['selected'] = True
            res['account_accts'] = True
        if 'account_account_ids' not in previous_options:
            res['account_account_ids'] = []
            res['account_acc_ids'] = []
        else:
            res['account_account_ids'] = previous_options['account_account_ids']
            res['account_acc_ids'] = previous_options['account_acc_ids']
        #_logger.warning('ReportPartnerLedger-_get_options-res: %s', res)
        return res

    @api.model
    def _get_query_sums(self, options, expanded_partner=None):
        ''' Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all partners.
        - sums for the initial balances.
        :param options:             The report options.
        :param expanded_partner:    An optional res.partner record that must be specified when expanding a line
                                    with of without the load more.
        :return:                    (query, params)
        '''
        #_logger.warning('ReportPartnerLedger-_get_query_sums-options: %s', options)
        params = []
        queries = []

        if expanded_partner is not None:
            domain = [('partner_id', '=', expanded_partner.id)]
        else:
            domain = []

        # Create the currency table.
        ct_query = self.env['res.currency']._get_query_currency_table(options)
        # Get sums for all partners.
        # period: [('date' <= options['date_to']), ('date' >= options['date_from'])]
        new_options = self._get_options_sum_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        params += where_params
        account_acc_ids = []
        if ('account_acc_ids' in options and len(options['account_acc_ids']) > 0):
            account_acc_ids = options['account_acc_ids']
        if ('account_acc_ids' in self._context and len(self._context.get('account_acc_ids')) > 0):
            account_acc_ids = self._context.get('account_acc_ids')
        #_logger.warning('ReportPartnerLedger-_get_query_sums-account_acc_ids: %s', account_acc_ids)
        where_aditional = (" AND account_move_line.account_id IN " + str(account_acc_ids).replace('[', '(').replace(']', ')') if (len(account_acc_ids) > 0) else "")
        #_logger.warning('ReportPartnerLedger-_get_query_sums-where_aditional: %s', where_aditional)
        queries.append('''
            SELECT
                account_move_line.partner_id        AS groupby,
                'sum'                               AS key,
                SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
            FROM %s LEFT JOIN account_account acc_acc ON account_move_line.account_id = acc_acc.id
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            WHERE %s %s
            GROUP BY account_move_line.partner_id
        ''' % (tables, ct_query, where_clause, where_aditional))

        # Get sums for the initial balance.
        # period: [('date' <= options['date_from'] - 1)]
        new_options = self._get_options_initial_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        params += where_params
        queries.append('''
            SELECT
                account_move_line.partner_id        AS groupby,
                'initial_balance'                   AS key,
                SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
            FROM %s LEFT JOIN account_account acc_acc ON account_move_line.account_id = acc_acc.id
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            WHERE %s %s
            GROUP BY account_move_line.partner_id
        ''' % (tables, ct_query, where_clause, where_aditional))

        return ' UNION ALL '.join(queries), params

    @api.model
    def _get_lines_without_partner(self, options, expanded_partner=None, offset=0, limit=0):
        ''' Get the detail of lines without partner reconciled with a line with a partner. Those lines should be
        considered as belonging the partner for the reconciled amount as it may clear some of the partner invoice/bill
        and they have to be accounted in the partner balance.'''

        params = []
        if expanded_partner:
            partner_clause = '= %s'
            params = [expanded_partner.id] + params
        else:
            partner_clause = 'IS NOT NULL'
        new_options = self._get_options_without_partner(options)
        params += [options['date']['date_from'], options['date']['date_to']]
        tables, where_clause, where_params = self._query_get(new_options, domain=[])
        params += where_params + [offset]
        limit_clause = ''
        account_acc_ids = []
        if ('account_acc_ids' in options and len(options['account_acc_ids']) > 0):
            account_acc_ids = options['account_acc_ids']
        if ('account_acc_ids' in self._context and len(self._context.get('account_acc_ids')) > 0):
            account_acc_ids = self._context.get('account_acc_ids')
        #_logger.warning('ReportPartnerLedger-_get_query_sums-account_acc_ids: %s', account_acc_ids)
        where_aditional = (" AND account_move_line.account_id IN " + str(account_acc_ids).replace('[', '(').replace(']', ')') if (len(account_acc_ids) > 0) else "")
        #_logger.warning('ReportPartnerLedger-_get_lines_without_partner-where_aditional: %s', where_aditional)
        if limit != 0:
            params += [limit]
            limit_clause = "LIMIT %s"
        query = '''
            SELECT
                account_move_line.id,
                account_move_line.date,
                account_move_line.date_maturity,
                account_move_line.name,
                account_move_line.ref,
                account_move_line.company_id,
                account_move_line.account_id,
                account_move_line.payment_id,
                aml_with_partner.partner_id,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                account_move_line.matching_number,
                CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END AS debit,
                CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END AS credit,
                CASE WHEN aml_with_partner.balance > 0 THEN -partial.amount ELSE partial.amount END AS balance,
                move.name         AS move_name,
                move.move_type    AS move_type,
                account.code                            AS account_code,
                account.name                            AS account_name,
                journal.code                            AS journal_code,
                journal.name                            AS journal_name,
                full_rec.name                           AS full_rec_name
            FROM {tables},
                account_partial_reconcile partial
                LEFT JOIN account_full_reconcile full_rec ON full_rec.id = partial.full_reconcile_id,
                account_move_line aml_with_partner
                LEFT JOIN account_move move ON aml_with_partner.move_id = move.id,
                account_journal journal,
                account_account account
            WHERE (account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id)
               AND account_move_line.partner_id IS NULL
               AND (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
               AND aml_with_partner.partner_id {partner_clause}
               AND journal.id = account_move_line.journal_id
               AND account.id = account_move_line.account_id
               AND partial.max_date BETWEEN %s AND %s
               AND {where_clause} {where_aditional}
            ORDER BY account_move_line.date, account_move_line.id
            OFFSET %s
            {limit_clause}
        '''.format(tables=tables, partner_clause=partner_clause, where_clause=where_clause, where_aditional=where_aditional, limit_clause=limit_clause)

        return query, params

    @api.model
    def _get_sums_without_partner(self, options, expanded_partner=None):
        ''' Get the sum of lines without partner reconciled with a line with a partner, grouped by partner. Those lines
        should be considered as belonging the partner for the reconciled amount as it may clear some of the partner
        invoice/bill and they have to be accounted in the partner balance.'''

        params = []
        if expanded_partner:
            partner_clause = '= %s'
            params = [expanded_partner.id]
        else:
            partner_clause = 'IS NOT NULL'

        new_options = self._get_options_without_partner(options)
        params = [options['date']['date_from']] + params + [options['date']['date_to']]
        tables, where_clause, where_params = self._query_get(new_options, domain=[])
        params += where_params
        account_acc_ids = []
        if ('account_acc_ids' in options and len(options['account_acc_ids']) > 0):
            account_acc_ids = options['account_acc_ids']
        if ('account_acc_ids' in self._context and len(self._context.get('account_acc_ids')) > 0):
            account_acc_ids = self._context.get('account_acc_ids')
        #_logger.warning('ReportPartnerLedger-_get_query_sums-account_acc_ids: %s', account_acc_ids)
        where_aditional = (" AND account_move_line.account_id IN " + str(account_acc_ids).replace('[', '(').replace(']', ')') if (len(account_acc_ids) > 0) else "")
        #_logger.warning('ReportPartnerLedger-_get_sums_without_partner-where_aditional: %s', where_aditional)
        query = '''
            SELECT
                aml_with_partner.partner_id AS groupby,
                SUM(CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END) AS debit,
                SUM(CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END) AS credit,
                SUM(CASE WHEN aml_with_partner.balance > 0 THEN -partial.amount ELSE partial.amount END) AS balance,
                CASE WHEN partial.max_date < %s THEN 'initial_balance' ELSE 'sum' END as key
            FROM {tables}, account_partial_reconcile partial, account_move_line aml_with_partner
            WHERE (account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id)
               AND account_move_line.partner_id IS NULL
               AND (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
               AND aml_with_partner.partner_id {partner_clause}
               AND partial.max_date <= %s
               AND {where_clause} {where_aditional}
            GROUP BY aml_with_partner.partner_id, key
        '''.format(tables=tables, partner_clause=partner_clause, where_aditional=where_aditional, where_clause=where_clause)
        return query, params

    @api.model
    def _get_query_amls(self, options, expanded_partner=None, offset=None, limit=None):
        ''' Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:             The report options.
        :param expanded_partner:    The res.partner record corresponding to the expanded line.
        :param offset:              The offset of the query (used by the load more).
        :param limit:               The limit of the query (used by the load more).
        :return:                    (query, params)
        '''
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        # Get sums for the account move lines.
        # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
        if expanded_partner is not None:
            domain = [('partner_id', '=', expanded_partner.id)]
        elif unfold_all:
            domain = []
        elif options['unfolded_lines']:
            domain = [('partner_id', 'in', [int(line[8:]) for line in options['unfolded_lines']])]

        new_options = self._get_options_sum_balance(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        ct_query = self.env['res.currency']._get_query_currency_table(options)
        account_acc_ids = []
        if ('account_acc_ids' in options and len(options['account_acc_ids']) > 0):
            account_acc_ids = options['account_acc_ids']
        if ('account_acc_ids' in self._context and len(self._context.get('account_acc_ids')) > 0):
            account_acc_ids = self._context.get('account_acc_ids')
        #_logger.warning('ReportPartnerLedger-_get_query_sums-account_acc_ids: %s', account_acc_ids)
        where_aditional = (" AND account_move_line.account_id IN " + str(account_acc_ids).replace('[', '(').replace(']', ')') if (len(account_acc_ids) > 0) else "")
        #_logger.warning('ReportPartnerLedger-_get_query_amls-where_aditional: %s', where_aditional)
        query = '''
            SELECT
                account_move_line.id,
                account_move_line.date,
                account_move_line.date_maturity,
                account_move_line.name,
                account_move_line.ref,
                account_move_line.company_id,
                account_move_line.account_id,
                account_move_line.payment_id,
                account_move_line.partner_id,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                account_move_line.matching_number,
                ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                move.name         AS move_name,
                company.currency_id                     AS company_currency_id,
                partner.name                            AS partner_name,
                move.move_type    AS move_type,
                account.code                            AS account_code,
                account.name                            AS account_name,
                journal.code                            AS journal_code,
                journal.name                            AS journal_name
            FROM %s
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            LEFT JOIN res_company company               ON company.id = account_move_line.company_id
            LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
            LEFT JOIN account_account account           ON account.id = account_move_line.account_id
            LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
            LEFT JOIN account_move move ON account_move_line.move_id = move.id
            WHERE %s %s
            ORDER BY account_move_line.date, account_move_line.id
        ''' % (tables, ct_query, where_clause, where_aditional)

        if offset:
            query += ' OFFSET %s '
            where_params.append(offset)
        if limit:
            query += ' LIMIT %s '
            where_params.append(limit)

        return query, where_params