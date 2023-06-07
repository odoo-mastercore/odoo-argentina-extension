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

class ReportGeneralLedger(models.AbstractModel):
    _inherit = "account.general.ledger.report.handler"
    
    filter_currencys = True
        
    def _custom_options_initializer(self, report, options, previous_options=None):
        # Remove multi-currency columns if needed
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if self.filter_currencys :
            currencies = [] #self.env['res.currency'].search([])
            #print('company_id: ', self.env.user.company_id)
            #print('currency_id: ', self.env.user.company_id.currency_id)
            #print('_context: ', self._context)
            if (self._context.get('allowed_company_ids')[0] == self.env.user.company_id.id):
                company = self.env.user.company_id
            else:
                company = self.env['res.company'].browse(self._context.get('allowed_company_ids')[0])
            currencies.append(company.currency_id)
            currencies.append(company.foreign_currency_id)
            options['currenciess'] = [{'id': c.id, 'name': c.name, 'selected': False} for c in currencies]
            if 'curr' in self._context:
                for c in options['currenciess']:
                    if c['id'] == self._context.get('curr'):
                        c['selected'] = True
            else:
                for c in options['currenciess']:
                    if c['id'] == company.currency_id.id:
                        c['selected'] = True

    @api.model
    def _get_query_sums(self, options_list, expanded_account=None):
        queries, params = super()._get_query_sums(options_list, expanded_account)
        if (self._context.get('allowed_company_ids')[0] == self.env.user.company_id.id):
            company = self.env.user.company_id
        else:
            company = self.env['res.company'].browse(self._context.get('allowed_company_ids')[0])
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = company.currency_id
        #_logger.info('_get_query_sums-queries_find(1): %s', queries.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")'))
        if (cur.id != company.currency_id.id):
            if (queries.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")') > 0):
                queries = queries.replace('COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,', 'ROUND(COALESCE(SUM((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN (CASE WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(account_move_line.amount_currency * account_move.l10n_ar_currency_rate, 2)) ELSE (ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 2)) END) ELSE account_move_line.amount_currency END) / (ROUND((1/currency_rate.rate),4))), 0.0), 2) AS amount_currency,')
                queries = queries.replace('SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,', '(CASE WHEN (SUM(ROUND(ROUND(account_move_line.debit/ROUND((1/currency_rate.rate),4),2) * currency_table.rate, currency_table.precision)) > 0) THEN SUM((CASE WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(ROUND(account_move_line.debit/account_move.l10n_ar_currency_rate,2) * currency_table.rate, currency_table.precision)) ELSE (ROUND(ROUND(account_move_line.debit/ROUND((1/currency_rate.rate),4),2) * currency_table.rate, currency_table.precision)) END)) ELSE (0.0) END) AS debit,')
                queries = queries.replace('SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,', '(CASE WHEN (SUM(ROUND(ROUND(account_move_line.credit/ROUND((1/currency_rate.rate),4),2) * currency_table.rate, currency_table.precision)) > 0) THEN SUM((CASE WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(ROUND(account_move_line.credit/account_move.l10n_ar_currency_rate,2) * currency_table.rate, currency_table.precision)) ELSE (ROUND(ROUND(account_move_line.credit/ROUND((1/currency_rate.rate),4),2) * currency_table.rate, currency_table.precision)) END)) ELSE (0.0) END) AS credit,')
                queries = queries.replace('SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance', '(CASE WHEN (SUM(ROUND(ROUND(account_move_line.balance/ROUND((1/currency_rate.rate),4),2) * currency_table.rate, currency_table.precision)) > 0) THEN SUM((CASE WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(ROUND(account_move_line.balance/account_move.l10n_ar_currency_rate,2) * currency_table.rate, currency_table.precision)) ELSE (ROUND(ROUND(account_move_line.balance/ROUND((1/currency_rate.rate),4),2) * currency_table.rate, currency_table.precision)) END)) ELSE (0.0) END) AS balance ')
                queries = queries.replace('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")', 'FROM "account_move_line" INNER JOIN "account_move" ON ("account_move"."id" = "account_move_line"."move_id") INNER JOIN "res_company" as "company" ON ("account_move_line"."company_id" = "company"."id") LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name" AND "company"."foreign_currency_id" = "currency_rate"."currency_id" AND "company"."id" = "currency_rate"."company_id") LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")')
                #_logger.info('agl-_get_query_sums-cur !=')
        else:
            if (queries.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")') > 0):
                queries = queries.replace('COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency', 'ROUND(COALESCE(SUM((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN (CASE WHEN (account_move.l10n_ar_currency_rate IS NOT NULL and account_move.l10n_ar_currency_rate > 1) THEN (ROUND(account_move_line.amount_currency * account_move.l10n_ar_currency_rate, 2)) ELSE (ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 2)) END) ELSE account_move_line.amount_currency END)), 0.0), 2) AS amount_currency')
                queries = queries.replace('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")', 'FROM "account_move_line" INNER JOIN "account_move" ON ("account_move"."id" = "account_move_line"."move_id") INNER JOIN "res_company" as "company" ON ("account_move_line"."company_id" = "company"."id") LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name" AND "company"."foreign_currency_id" = "currency_rate"."currency_id" AND "company"."id" = "currency_rate"."company_id") LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")')
                #_logger.info('agl-_get_query_sums-cur ==')
        #_logger.info('agl-_get_query_sums-modif(queries)===>: %s', queries)
        #_logger.info('agl-_get_query_sums-modif(params)===>: %s', params)
        return queries, params

    @api.model
    def _get_query_amls(self, report, options, expanded_account_ids, offset=0, limit=None):
        query, where_params = super()._get_query_amls(report, options, expanded_account_ids, offset, limit)
        if (self._context.get('allowed_company_ids')[0] == self.env.user.company_id.id):
            company = self.env.user.company_id
        else:
            company = self.env['res.company'].browse(self._context.get('allowed_company_ids')[0])
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = company.currency_id
        #_logger.info('agl-_get_query_amls-query_find(1): %s', query.find('FROM "account_move_line"'))
        if (cur.id != company.currency_id.id):
            if (query.find('FROM "account_move_line"') > 0):
                query = query.replace('account_move_line.amount_currency,', 'ROUND(COALESCE((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN (CASE WHEN (move.l10n_ar_currency_rate IS NOT NULL and move.l10n_ar_currency_rate > 1) THEN (ROUND(account_move_line.amount_currency * move.l10n_ar_currency_rate, 2)) ELSE (ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 2)) END) ELSE account_move_line.amount_currency END) / (CASE WHEN (move.l10n_ar_currency_rate IS NOT NULL and move.l10n_ar_currency_rate > 1) THEN (move.l10n_ar_currency_rate) ELSE (ROUND((1/currency_rate.rate),4)) END), 0.0), 2) AS amount_currency,')
                query = query.replace('ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,','(CASE WHEN (ROUND(ROUND((account_move_line.debit / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision) > 0) THEN (CASE WHEN (move.l10n_ar_currency_rate IS NOT NULL and move.l10n_ar_currency_rate > 1) THEN (ROUND(ROUND((account_move_line.debit / move.l10n_ar_currency_rate), 2) * currency_table.rate, currency_table.precision)) ELSE (ROUND(ROUND((account_move_line.debit / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision)) END) ELSE (0.0) END) AS debit,')
                query = query.replace('ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,','(CASE WHEN (ROUND(ROUND((account_move_line.credit / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision) > 0) THEN (CASE WHEN (move.l10n_ar_currency_rate IS NOT NULL and move.l10n_ar_currency_rate > 1) THEN (ROUND(ROUND((account_move_line.credit / move.l10n_ar_currency_rate), 2) * currency_table.rate, currency_table.precision)) ELSE (ROUND(ROUND((account_move_line.credit / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision)) END) ELSE (0.0) END) AS credit,')
                query = query.replace('ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,','(CASE WHEN (ROUND(ROUND((account_move_line.balance / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision) > 0) THEN (CASE WHEN (move.l10n_ar_currency_rate IS NOT NULL and move.l10n_ar_currency_rate > 1) THEN (ROUND(ROUND((account_move_line.balance / move.l10n_ar_currency_rate), 2) * currency_table.rate, currency_table.precision)) ELSE (ROUND(ROUND((account_move_line.balance / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision)) END) ELSE (0.0) END) AS balance,')
                query = query.replace('FROM "account_move_line"', 'FROM "account_move_line" INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id") LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id" AND "company_rate"."id" = "currency_rate"."company_id") ')
        else:
            if (query.find('FROM "account_move_line"') > 0):
                query = query.replace('account_move_line.amount_currency,', 'ROUND(COALESCE((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN (CASE WHEN (move.l10n_ar_currency_rate IS NOT NULL and move.l10n_ar_currency_rate > 1) THEN (ROUND(account_move_line.amount_currency * move.l10n_ar_currency_rate, 2)) ELSE (ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 2)) END) ELSE account_move_line.amount_currency END), 0.0), 2) AS amount_currency,')
                query = query.replace('FROM "account_move_line"', 'FROM "account_move_line" INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id") LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id" AND "company_rate"."id" = "currency_rate"."company_id") ')
        #_logger.info('agl-_get_query_amls-modif(query)===>: %s', query)
        #_logger.info('agl-_get_query_amls-modif(where_params)===>: %s', where_params)
        return query, where_params