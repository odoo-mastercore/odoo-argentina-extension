# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json

from odoo import models, api, _, fields
from datetime import datetime, timedelta
from odoo.tools.misc import format_date
from collections import defaultdict

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter
import io
import logging
_logger = logging.getLogger(__name__)

class ReportPartnerLedger(models.AbstractModel):
    _inherit = "account.partner.ledger.report.handler"
    
    filter_currencys = True

    def _custom_options_initializer(self, report, options, previous_options=None):
        #print('_custom_options_initializer-options: ', options)
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if self.filter_currencys :
            currencies = [] #self.env['res.currency'].search([])
            if (self._context.get('allowed_company_ids')[0] == self.env.user.company_id.id):
                company = self.env.user.company_id
            else:
                company = self.env['res.company'].browse(self._context.get('allowed_company_ids')[0])
            currencies.append(company.currency_id)
            currencies.append(company.foreign_currency_id)
            options['foreign_currency_id'] = company.foreign_currency_id.id
            options['currenciess'] = [{'id': c.id, 'name': c.name, 'selected': False} for c in currencies]
            if 'curr' in self._context:
                for c in options['currenciess']:
                    if c['id'] == self._context.get('curr'):
                        c['selected'] = True
            else:
                for c in options['currenciess']:
                    if c['id'] == company.currency_id.id:
                        c['selected'] = True

    def _get_query_sums(self, options):
        query, params = super()._get_query_sums(options)
        if (self._context.get('allowed_company_ids')[0] == self.env.user.company_id.id):
            company = self.env.user.company_id
        else:
            company = self.env['res.company'].browse(self._context.get('allowed_company_ids')[0])
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = company.currency_id
        #_logger.info('apl-_get_query_sums-query_find(1): %s', query.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")'))
        if (cur.id != company.currency_id.id):
            if (query.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")') > 0):
                query = query.replace('SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit', '(CASE WHEN (LENGTH(CAST(SUM(ROUND(account_move_line.debit / ROUND((1/currency_table.rate),4), 6)) AS TEXT)) > 0) THEN SUM(CASE WHEN (account_move_line.aux_inverse_currency_rate IS NOT NULL AND account_move_line.aux_inverse_currency_rate > 1) THEN (ROUND(account_move_line.debit / account_move_line.aux_inverse_currency_rate::numeric, 6)) WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(account_move_line.debit / account_move.l10n_ar_currency_rate, 6)) ELSE (ROUND(account_move_line.debit / ROUND((1/currency_rate.rate),4), 6)) END) ELSE (0.0) END) AS debit')
                query = query.replace('SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit', '(CASE WHEN (LENGTH(CAST(SUM(ROUND(account_move_line.credit / ROUND((1/currency_table.rate),4), 6)) AS TEXT)) > 0) THEN SUM(CASE WHEN (account_move_line.aux_inverse_currency_rate IS NOT NULL AND account_move_line.aux_inverse_currency_rate > 1) THEN (ROUND(account_move_line.credit / account_move_line.aux_inverse_currency_rate::numeric, 6)) WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(account_move_line.credit / account_move.l10n_ar_currency_rate, 6)) ELSE (ROUND(account_move_line.credit / ROUND((1/currency_rate.rate),4), 6)) END) ELSE (0.0) END) AS credit')
                query = query.replace('SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance', '(CASE WHEN (LENGTH(CAST(SUM(ROUND(account_move_line.balance / ROUND((1/currency_table.rate),4), 6)) AS TEXT)) > 0) THEN SUM(CASE WHEN (account_move_line.aux_inverse_currency_rate IS NOT NULL AND account_move_line.aux_inverse_currency_rate > 1) THEN (ROUND(account_move_line.balance / account_move_line.aux_inverse_currency_rate::numeric, 6)) WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(account_move_line.balance / account_move.l10n_ar_currency_rate, 6)) ELSE (ROUND(account_move_line.balance / ROUND((1/currency_rate.rate),4), 6)) END) ELSE (0.0) END) AS balance')
                query = query.replace('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")', 'FROM "account_move_line" INNER JOIN "account_move" ON ("account_move"."id" = "account_move_line"."move_id") INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id") LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id" AND "company_rate"."id" = "currency_rate"."company_id") LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id") LEFT JOIN account_journal journal ON (journal.id = account_move_line.journal_id) ')
                query = query.replace('GROUP BY account_move_line.partner_id', ' AND (journal.exclude_report is NULL or journal.exclude_report = False) GROUP BY account_move_line.partner_id')
                #_logger.info('apl-_get_query_sums- cur !=')
        else:
            if (query.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")') > 0):
                query = query.replace('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")', 'FROM "account_move_line" INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id") LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id" AND "company_rate"."id" = "currency_rate"."company_id") LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id") LEFT JOIN account_journal journal ON (journal.id = account_move_line.journal_id) ')
                query = query.replace('GROUP BY account_move_line.partner_id', ' AND (journal.exclude_report is NULL or journal.exclude_report = False) GROUP BY account_move_line.partner_id')
                #_logger.info('apl-_get_query_sums- cur ==')
        #_logger.info('apl-_get_query_sums-query==>: %s', query)
        #_logger.info('apl-_get_query_sums-params==>: %s', params)
        return query, params

    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        rslt = {partner_id: [] for partner_id in partner_ids}

        partner_ids_wo_none = [x for x in partner_ids if x]
        directly_linked_aml_partner_clauses = []
        directly_linked_aml_partner_params = []
        indirectly_linked_aml_partner_params = []
        indirectly_linked_aml_partner_clause = 'aml_with_partner.partner_id IS NOT NULL'
        if None in partner_ids:
            directly_linked_aml_partner_clauses.append('account_move_line.partner_id IS NULL')
        if partner_ids_wo_none:
            directly_linked_aml_partner_clauses.append('account_move_line.partner_id IN %s')
            directly_linked_aml_partner_params.append(tuple(partner_ids_wo_none))
            indirectly_linked_aml_partner_clause = 'aml_with_partner.partner_id IN %s'
            indirectly_linked_aml_partner_params.append(tuple(partner_ids_wo_none))
        directly_linked_aml_partner_clause = '(' + ' OR '.join(directly_linked_aml_partner_clauses) + ')'

        ct_query = self.env['res.currency']._get_query_currency_table(options)
        queries = []
        all_params = []
        lang = self.env.lang or get_lang(self.env).code
        journal_name = f"COALESCE(journal.name->>'{lang}', journal.name->>'en_US')" if \
            self.pool['account.journal'].name.translate else 'journal.name'
        account_name = f"COALESCE(account.name->>'{lang}', account.name->>'en_US')" if \
            self.pool['account.account'].name.translate else 'account.name'
        report = self.env.ref('account_reports.partner_ledger_report')
        for column_group_key, group_options in report._split_options_per_column_group(options).items():
            tables, where_clause, where_params = report._query_get(group_options, 'strict_range')

            all_params += [
                column_group_key,
                *where_params,
                *directly_linked_aml_partner_params,
                column_group_key,
                *indirectly_linked_aml_partner_params,
                *where_params,
                group_options['date']['date_from'],
                group_options['date']['date_to'],
            ]

            # For the move lines directly linked to this partner
            queries.append(f'''
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
                    account_move.name                                                                AS move_name,
                    account_move.move_type                                                           AS move_type,
                    account.code                                                                     AS account_code,
                    {account_name}                                                                   AS account_name,
                    journal.code                                                                     AS journal_code,
                    {journal_name}                                                                   AS journal_name,
                    %s                                                                               AS column_group_key,
                    'directly_linked_aml'                                                            AS key
                FROM {tables}
                JOIN account_move ON account_move.id = account_move_line.move_id
                LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                LEFT JOIN res_company company               ON company.id = account_move_line.company_id
                LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
                LEFT JOIN account_account account           ON account.id = account_move_line.account_id
                LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
                WHERE {where_clause} AND {directly_linked_aml_partner_clause}
                ORDER BY account_move_line.date, account_move_line.id
            ''')

            # For the move lines linked to no partner, but reconciled with this partner. They will appear in grey in the report
            queries.append(f'''
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
                    CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE ROUND(
                        partial.amount * currency_table.rate, currency_table.precision
                    ) END                                                                               AS debit,
                    CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE ROUND(
                        partial.amount * currency_table.rate, currency_table.precision
                    ) END                                                                               AS credit,
                    - sign(aml_with_partner.balance) * ROUND(
                        partial.amount * currency_table.rate, currency_table.precision
                    )                                                                                   AS balance,
                    account_move.name                                                                   AS move_name,
                    account_move.move_type                                                              AS move_type,
                    account.code                                                                        AS account_code,
                    {account_name}                                                                      AS account_name,
                    journal.code                                                                        AS journal_code,
                    {journal_name}                                                                      AS journal_name,
                    %s                                                                                  AS column_group_key,
                    'indirectly_linked_aml'                                                             AS key
                FROM {tables}
                    LEFT JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id,
                    account_partial_reconcile partial,
                    account_move,
                    account_move_line aml_with_partner,
                    account_journal journal,
                    account_account account
                WHERE
                    (account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id)
                    AND account_move_line.partner_id IS NULL
                    AND account_move.id = account_move_line.move_id
                    AND (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
                    AND {indirectly_linked_aml_partner_clause}
                    AND journal.id = account_move_line.journal_id
                    AND account.id = account_move_line.account_id
                    AND {where_clause}
                    AND partial.max_date BETWEEN %s AND %s
                ORDER BY account_move_line.date, account_move_line.id
            ''')

        query = '(' + ') UNION ALL ('.join(queries) + ')'

        if offset:
            query += ' OFFSET %s '
            all_params.append(offset)

        if limit:
            query += ' LIMIT %s '
            all_params.append(limit)
        #print('_get_aml_values-query: ', query)
        #print('_get_query_amls-all_params: ', all_params)
        #print('_get_aml_values-find: ', query.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")'))
        if (self._context.get('allowed_company_ids')[0] == self.env.user.company_id.id):
            company = self.env.user.company_id
        else:
            company = self.env['res.company'].browse(self._context.get('allowed_company_ids')[0])
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = company.currency_id
        #_logger.info('apl-_get_query_amls-query_find==>: %s', query.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")'))
        if (cur.id != company.currency_id.id):
            if (query.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")') > 0):
                query = query.replace('account_move_line.currency_id,', "account_move_line.currency_id, res_currency.name AS aml_currency_name,")
                query = query.replace('account_move_line.amount_currency,', 'ROUND(COALESCE((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN (CASE WHEN (account_move_line.aux_inverse_currency_rate IS NOT NULL and account_move_line.aux_inverse_currency_rate > 1) THEN (ROUND(account_move_line.amount_currency * account_move_line.aux_inverse_currency_rate::numeric, 6)) WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(account_move_line.amount_currency * account_move.l10n_ar_currency_rate, 6)) ELSE (ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 6)) END) ELSE account_move_line.amount_currency END) / (CASE WHEN (account_move_line.aux_inverse_currency_rate IS NOT NULL and account_move_line.aux_inverse_currency_rate > 1) THEN (account_move_line.aux_inverse_currency_rate::numeric) WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (account_move.l10n_ar_currency_rate) ELSE (ROUND((1/currency_rate.rate),4)) END), 0.0), 6) AS amount_currency,')
                query = query.replace('account_move.name                                                                AS move_name,', 'account_move.name         AS move_name, (select count(distinct am.id) FROM account_move_line aml LEFT JOIN account_move am ON (aml.move_id = am.id) where am.name = account_move.name AND aml.partner_id = "account_move_line"."partner_id") AS count_move_name,')
                query = query.replace('account_move.name                                                                   AS move_name,', 'account_move.name         AS move_name, (select count(distinct am.id) FROM account_move_line aml LEFT JOIN account_move am ON (aml.move_id = am.id) where am.name = account_move.name AND aml.partner_id = "account_move_line"."partner_id") AS count_move_name,')
                query = query.replace('ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,','(CASE WHEN (account_move_line.debit > 0) THEN (CASE WHEN (account_move_line.aux_inverse_currency_rate IS NOT NULL and account_move_line.aux_inverse_currency_rate > 1) THEN (ROUND(ROUND((account_move_line.debit / account_move_line.aux_inverse_currency_rate::numeric), 6) * currency_table.rate, currency_table.precision)) WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(ROUND((account_move_line.debit / account_move.l10n_ar_currency_rate), 6) * currency_table.rate, currency_table.precision)) WHEN (currency_rate.rate > 0) THEN (ROUND(ROUND((account_move_line.debit / ROUND((1/currency_rate.rate),4)), 6) * currency_table.rate, currency_table.precision)) ELSE (0.0) END) ELSE (0.0) END) AS debit,')
                query = query.replace('ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,','(CASE WHEN (account_move_line.credit > 0) THEN (CASE WHEN (account_move_line.aux_inverse_currency_rate IS NOT NULL and account_move_line.aux_inverse_currency_rate > 1) THEN (ROUND(ROUND((account_move_line.credit / account_move_line.aux_inverse_currency_rate::numeric), 6) * currency_table.rate, currency_table.precision)) WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(ROUND((account_move_line.credit / account_move.l10n_ar_currency_rate), 6) * currency_table.rate, currency_table.precision)) WHEN (currency_rate.rate > 0) THEN (ROUND(ROUND((account_move_line.credit / ROUND((1/currency_rate.rate),4)), 6) * currency_table.rate, currency_table.precision)) ELSE (0.0) END) ELSE (0.0) END) AS credit,')
                query = query.replace('ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,','(CASE WHEN (account_move_line.balance > 0) THEN (CASE WHEN (account_move_line.aux_inverse_currency_rate IS NOT NULL and account_move_line.aux_inverse_currency_rate > 1) THEN (ROUND(ROUND((account_move_line.balance / account_move_line.aux_inverse_currency_rate::numeric), 6) * currency_table.rate, currency_table.precision)) WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(ROUND((account_move_line.balance / account_move.l10n_ar_currency_rate), 6) * currency_table.rate, currency_table.precision)) WHEN (currency_rate.rate > 0) THEN (ROUND(ROUND((account_move_line.balance / ROUND((1/currency_rate.rate),4)), 6) * currency_table.rate, currency_table.precision)) ELSE (0.0) END) ELSE (0.0) END) AS balance,')
                query = query.replace('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")', 'FROM "account_move_line" INNER JOIN "res_currency" ON ("account_move_line"."currency_id" = "res_currency"."id") INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id") LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id" AND "company_rate"."id" = "currency_rate"."company_id") LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")')
                query = query.replace('ORDER BY account_move_line.date, account_move_line.id', ' AND (journal.exclude_report is NULL or journal.exclude_report = False) ORDER BY account_move_line.date, account_move_line.id')
                #_logger.info('apl-_get_query_amls-cur !=')
        else:
            if (query.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")') > 0):
                query = query.replace('account_move_line.currency_id,', "account_move_line.currency_id, res_currency.name AS aml_currency_name,")
                query = query.replace('account_move_line.amount_currency,', "ROUND(COALESCE((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN (CASE WHEN (move_type = 'in_invoice' or move_type = 'out_invoice') THEN (account_move_line.balance) ELSE (CASE WHEN (account_move_line.aux_inverse_currency_rate IS NOT NULL and account_move_line.aux_inverse_currency_rate > 1) THEN (ROUND(account_move_line.amount_currency * account_move_line.aux_inverse_currency_rate::numeric, 6)) WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(account_move_line.amount_currency * account_move.l10n_ar_currency_rate, 6)) ELSE (ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 6)) END) END) ELSE account_move_line.amount_currency END), 0.0), 6) AS amount_currency,")
                query = query.replace('account_move.name                                                                AS move_name,', 'account_move.name         AS move_name, (select count(distinct am.id) FROM account_move_line aml LEFT JOIN account_move am ON (aml.move_id = am.id) where am.name = account_move.name  AND aml.partner_id = "account_move_line"."partner_id") AS count_move_name,')
                query = query.replace('account_move.name                                                                   AS move_name,', 'account_move.name         AS move_name, (select count(distinct am.id) FROM account_move_line aml LEFT JOIN account_move am ON (aml.move_id = am.id) where am.name = account_move.name AND aml.partner_id = "account_move_line"."partner_id") AS count_move_name,')
                query = query.replace('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")', 'FROM "account_move_line" INNER JOIN "res_currency" ON ("account_move_line"."currency_id" = "res_currency"."id") INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id") LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id" AND "company_rate"."id" = "currency_rate"."company_id") LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")')
                query = query.replace('ORDER BY account_move_line.date, account_move_line.id', ' AND (journal.exclude_report is NULL or journal.exclude_report = False) ORDER BY account_move_line.date, account_move_line.id')
                #_logger.info('apl-_get_query_amls-cur ==')
        #_logger.info('apl-_get_query_amls-query==>: %s', query)
        #_logger.info('apl-_get_query_amls-query.find(LIMIT)==>: %s', query.find('LIMIT'))
        if (query.find('LIMIT') > 0):
            query = query[0:query.find('LIMIT')]
            all_params.remove(all_params[len(all_params) -1])
        #_logger.info('apl-_get_query_amls-query[0:query.find(OFFSET)==>: %s', query.find('OFFSET'))
        if (query.find('OFFSET') > 0):
            query = query[0:query.find('OFFSET')]
            all_params.remove(all_params[len(all_params) -1])
        #_logger.info('apl-_get_query_amls-query==>: %s', query)
        #_logger.info('apl-_get_query_amls-all_params==>: %s', all_params)

        self._cr.execute(query, all_params)
        for aml_result in self._cr.dictfetchall():
            _logger.info('apl-_get_query_amls-aml_result: %s', aml_result)
            if aml_result['key'] == 'indirectly_linked_aml':

                # Append the line to the partner found through the reconciliation.
                if aml_result['partner_id'] in rslt:
                    rslt[aml_result['partner_id']].append(aml_result)

                # Balance it with an additional line in the Unknown Partner section but having reversed amounts.
                if None in rslt:
                    rslt[None].append({
                        **aml_result,
                        'debit': aml_result['credit'],
                        'credit': aml_result['debit'],
                        'balance': -aml_result['balance'],
                    })
            else:
                rslt[aml_result['partner_id']].append(aml_result)

        return rslt

    def _report_expand_unfoldable_line_partner_ledger(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        #print('_report_expand_unfoldable_line_partner_ledger-self===> ', self)
        def init_load_more_progress(line_dict):
            return {
                column['column_group_key']: line_col.get('no_format', 0)
                for column, line_col in  zip(options['columns'], line_dict['columns'])
                if column['expression_label'] == 'balance'
            }

        report = self.env.ref('account_reports.partner_ledger_report')
        markup, model, record_id = report._parse_line_id(line_dict_id)[-1]

        if model != 'res.partner':
            raise UserError(_("Wrong ID for partner ledger line to expand: %s", line_dict_id))

        prefix_groups_count = 0
        for markup, dummy1, dummy2 in report._parse_line_id(line_dict_id):
            if markup.startswith('groupby_prefix_group:'):
                prefix_groups_count += 1
        level_shift = prefix_groups_count * 2

        lines = []

        # Get initial balance
        if offset == 0:
            if unfold_all_batch_data:
                init_balance_by_col_group = unfold_all_batch_data['initial_balances'][record_id]
            else:
                init_balance_by_col_group = self._get_initial_balance_values([record_id], options)[record_id]
            initial_balance_line = report._get_partner_and_general_ledger_initial_balance_line(options, line_dict_id, init_balance_by_col_group, level_shift=level_shift)
            if initial_balance_line:
                lines.append(initial_balance_line)

                # For the first expansion of the line, the initial balance line gives the progress
                progress = init_load_more_progress(initial_balance_line)

        limit_to_load = report.load_more_limit + 1 if report.load_more_limit and not self._context.get('print_mode') else None

        if unfold_all_batch_data:
            aml_results = unfold_all_batch_data['aml_values'][record_id]
        else:
            aml_results = self._get_aml_values(options, [record_id], offset=offset, limit=limit_to_load)[record_id]

        has_more = False
        treated_results_count = 0
        next_progress = progress
        gp_amount_currency = 0
        gp_debit = 0
        gp_credit = 0
        gp_balance = 0
        gp_cumulated_init_balance = 0
        gp_cumulated_balance = 0
        count_move_name = 0
        for result in aml_results:
            if not self._context.get('print_mode') and report.load_more_limit and treated_results_count == report.load_more_limit:
                # We loaded one more than the limit on purpose: this way we know we need a "load more" line
                has_more = True
                break
            if (result['count_move_name'] == 1):
                count_move_name = 0
                gp_amount_currency = 0
                gp_debit = 0
                gp_credit = 0
                gp_balance = 0
            else:
                count_move_name = count_move_name + 1
                gp_amount_currency = gp_amount_currency + result['amount_currency']
                gp_debit = gp_debit + result['debit']
                gp_credit = gp_credit + result['credit']
                gp_balance = gp_balance + result['balance']
                result['journal_code'] = 'GdP'
                result['amount_currency'] = gp_amount_currency
                result['debit'] = gp_debit
                result['credit'] = gp_credit
                result['balance'] = gp_balance
                result['no_format'] = gp_cumulated_init_balance - gp_credit
            if (result['count_move_name'] == count_move_name) or result['count_move_name'] == 1:
                new_line = self._get_report_line_move_line(options, result, line_dict_id, next_progress, level_shift=level_shift)
                #print('_report_expand_unfoldable_line_partner_ledger-new_line===> ', new_line)
                #print('_report_expand_unfoldable_line_partner_ledger-no_format===> ', new_line['columns'][(len(new_line['columns']) - 1)]['no_format'])
                lines.append(new_line)
                next_progress = init_load_more_progress(new_line)
                count_move_name = 0
                gp_amount_currency = 0
                gp_debit = 0
                gp_credit = 0
                gp_balance = 0
                gp_cumulated_init_balance = 0
                gp_cumulated_balance = 0
                gp_cumulated_init_balance = new_line['columns'][(len(new_line['columns']) - 1)]['no_format']

            treated_results_count += 1

        return {
            'lines': lines,
            'offset_increment': treated_results_count,
            'has_more': has_more,
            'progress': json.dumps(next_progress)
        }

    def _get_report_line_move_line(self, options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=0):
        if aml_query_result['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move.line'

        columns = []
        report = self.env['account.report']
        for column in options['columns']:
            col_expr_label = column['expression_label']
            if col_expr_label == 'ref':
                if (aml_query_result['move_type'] == 'in_invoice' or aml_query_result['move_type'] == 'out_invoice'):
                    col_value = aml_query_result['move_name'] if aml_query_result['payment_id'] else report._format_aml_name(aml_query_result['name'], aml_query_result['ref'], ((aml_query_result['move_name'] + ' (' + aml_query_result['aml_currency_name']+ ')') if (not aml_query_result['move_name'] is None) else aml_query_result['move_name']))
                else:
                    col_value = aml_query_result['move_name'] if aml_query_result['payment_id'] else report._format_aml_name(aml_query_result['name'], aml_query_result['ref'], aml_query_result['move_name'])
            else:
                col_value = aml_query_result[col_expr_label] if column['column_group_key'] == aml_query_result['column_group_key'] else None

            if col_value is None:
                columns.append({})
            else:
                col_class = 'number'

                if col_expr_label == 'date_maturity':
                    formatted_value = format_date(self.env, fields.Date.from_string(col_value))
                    col_class = 'date'
                elif col_expr_label == 'amount_currency':
                    currency = self.env['res.currency'].browse(aml_query_result['currency_id'])
                    formatted_value = report.format_value(col_value, currency=currency, figure_type=column['figure_type'])
                elif col_expr_label == 'balance':
                    col_value += init_bal_by_col_group[column['column_group_key']]
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'], blank_if_zero=column['blank_if_zero'])
                else:
                    if col_expr_label == 'ref':
                        col_class = 'o_account_report_line_ellipsis'
                    elif col_expr_label not in ('debit', 'credit'):
                        col_class = ''
                    formatted_value = report.format_value(col_value, figure_type=column['figure_type'])
                #print('formatted_value: ', formatted_value)
                #print('col_value: ', col_value)
                #print('col_class: ', col_class)
                columns.append({
                    'name': formatted_value,
                    'no_format': col_value,
                    'class': col_class,
                })

        return {
            'id': report._get_generic_line_id('account.move.line', aml_query_result['id'], parent_line_id=partner_line_id),
            'parent_id': partner_line_id,
            'name': format_date(self.env, aml_query_result['date']),
            'class': 'text-muted' if aml_query_result['key'] == 'indirectly_linked_aml' else 'text',  # do not format as date to prevent text centering
            'columns': columns,
            'caret_options': caret_type,
            'level': 2 + level_shift,
        }

    def _query_partners(self, options):
        def assign_sum(row):
            fields_to_assign = ['balance', 'debit', 'credit']
            for field in fields_to_assign:
                #_logger.info('apl-assign_sum-field==>: %s', field)
                #_logger.info('apl-assign_sum-row[field]==>: %s', row[field])
                if row[field] is None:
                    row[field] = 0.0
                    #_logger.info('apl-assign_sum-row[field]-force==>: %s', row[field])
            if any(not company_currency.is_zero(row[field]) for field in fields_to_assign):
                groupby_partners.setdefault(row['groupby'], defaultdict(lambda: defaultdict(float)))
                for field in fields_to_assign:
                    groupby_partners[row['groupby']][row['column_group_key']][field] += row[field]

        company_currency = self.env.company.currency_id

        # Execute the queries and dispatch the results.
        query, params = self._get_query_sums(options)

        groupby_partners = {}

        self._cr.execute(query, params)
        for res in self._cr.dictfetchall():
            assign_sum(res)

        # Correct the sums per partner, for the lines without partner reconciled with a line having a partner
        query, params = self._get_sums_without_partner(options)

        self._cr.execute(query, params)
        totals = {}
        for total_field in ['debit', 'credit', 'balance']:
            totals[total_field] = {col_group_key: 0 for col_group_key in options['column_groups']}

        for row in self._cr.dictfetchall():
            totals['debit'][row['column_group_key']] += row['debit']
            totals['credit'][row['column_group_key']] += row['credit']
            totals['balance'][row['column_group_key']] += row['balance']

            if row['groupby'] not in groupby_partners:
                continue

            assign_sum(row)

        if None in groupby_partners:
            # Debit/credit are inverted for the unknown partner as the computation is made regarding the balance of the known partner
            for column_group_key in options['column_groups']:
                groupby_partners[None][column_group_key]['debit'] += totals['credit'][column_group_key]
                groupby_partners[None][column_group_key]['credit'] += totals['debit'][column_group_key]
                groupby_partners[None][column_group_key]['balance'] -= totals['balance'][column_group_key]

        # Retrieve the partners to browse.
        # groupby_partners.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        if groupby_partners:
            # Note a search is done instead of a browse to preserve the table ordering.
            partners = self.env['res.partner'].with_context(active_test=False).search([('id', 'in', list(groupby_partners.keys()))])
        else:
            partners = []

        # Add 'Partner Unknown' if needed
        if None in groupby_partners.keys():
            partners = [p for p in partners] + [None]

        return [(partner, groupby_partners[partner.id if partner else None]) for partner in partners]
