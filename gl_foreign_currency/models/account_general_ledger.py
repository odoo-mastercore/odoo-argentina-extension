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
        #print('_get_query_sums-queries: ', queries)
        if (self._context.get('allowed_company_ids')[0] == self.env.user.company_id.id):
            company = self.env.user.company_id
        else:
            company = self.env['res.company'].browse(self._context.get('allowed_company_ids')[0])
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = company.currency_id
        if (cur.id != company.currency_id.id):
            if (queries.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")') > 0):
                queries = queries.replace('COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency', 'ROUND(COALESCE(SUM((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 2) ELSE account_move_line.amount_currency END) / (ROUND((1/currency_rate.rate),4))), 0.0), 2) AS amount_currency')
                queries = queries.replace('SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,', 'SUM(ROUND(ROUND(account_move_line.debit/ROUND((1/currency_rate.rate),4),2) * currency_table.rate, currency_table.precision)) AS debit,')
                queries = queries.replace('SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,', 'SUM(ROUND(ROUND(account_move_line.credit/ROUND((1/currency_rate.rate),4),2) * currency_table.rate, currency_table.precision)) AS credit,')
                queries = queries.replace('SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance', 'SUM(ROUND(ROUND(account_move_line.balance/ROUND((1/currency_rate.rate),4),2) * currency_table.rate, currency_table.precision)) AS balance ')
                queries = queries.replace('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")', 'FROM "account_move_line" INNER JOIN "res_company" as "company" ON ("account_move_line"."company_id" = "company"."id") LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name" AND "company"."foreign_currency_id" = "currency_rate"."currency_id") LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")')
        else:
            if (queries.find('FROM "account_move_line" LEFT JOIN "account_move" AS "account_move_line__move_id"') > 0):
                queries = queries.replace('COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency', 'ROUND(COALESCE(SUM((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 2) ELSE account_move_line.amount_currency END)), 0.0), 2) AS amount_currency')
                queries = queries.replace('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")', 'FROM "account_move_line" INNER JOIN "res_company" as "company" ON ("account_move_line"."company_id" = "company"."id") LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name" AND "company"."foreign_currency_id" = "currency_rate"."currency_id") LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")')
                #print('_get_query_sums-queries(2): ', queries)
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
        if (cur.id != company.currency_id.id):
            if (query.find('FROM "account_move_line"') > 0):
                query = query.replace('account_move_line.amount_currency,', 'ROUND(COALESCE((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 2) ELSE account_move_line.amount_currency END) / (ROUND((1/currency_rate.rate),4)), 0.0), 2) AS amount_currency,')
                query = query.replace('ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,','ROUND(ROUND((account_move_line.debit / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision)   AS debit,')
                query = query.replace('ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,','ROUND(ROUND((account_move_line.credit / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision)  AS credit,')
                query = query.replace('ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,','ROUND(ROUND((account_move_line.balance / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision) AS balance,')
                query = query.replace('FROM "account_move_line"', 'FROM "account_move_line" INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id") LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id") ')
        else:
            if (query.find('FROM "account_move_line"') > 0):
                query = query.replace('account_move_line.amount_currency,', 'ROUND(COALESCE((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 2) ELSE account_move_line.amount_currency END), 0.0), 2) AS amount_currency,')
                query = query.replace('FROM "account_move_line"', 'FROM "account_move_line" INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id") LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id") ')
        return query, where_params