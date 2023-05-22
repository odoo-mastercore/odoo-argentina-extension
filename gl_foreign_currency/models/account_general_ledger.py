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
            currencies.append(self.env.user.company_id.currency_id)
            currencies.append(self.env.user.company_id.foreign_currency_id)
            options['currenciess'] = [{'id': c.id, 'name': c.name, 'selected': False} for c in currencies]
            if 'curr' in self._context:
                for c in options['currenciess']:
                    if c['id'] == self._context.get('curr'):
                        c['selected'] = True
            else:
                for c in options['currenciess']:
                    if c['id'] == self.env.user.company_id.currency_id.id:
                        c['selected'] = True

    '''@api.model
    def _get_aml_line(self, options, account, aml, cumulated_balance):
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = self.env.user.company_id.currency_id
        if aml['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move'

        if aml['ref'] and aml['name']:
            title = '%s - %s' % (aml['name'], aml['ref'])
        elif aml['ref']:
            title = aml['ref']
        elif aml['name']:
            title = aml['name']
        else:
            title = ''

        if aml['currency_id']:
            currency = self.env['res.currency'].browse(aml['currency_id'])
        else:
            currency = False
        columns = [
            {'name': format_date(self.env, aml['date']), 'class': 'date'},
            {'name': self._format_aml_name(aml['name'], aml['ref'], aml['move_name']), 'title': title,'class': 'whitespace_print o_account_report_line_ellipsis'},
            {'name': aml['partner_name'], 'title': aml['partner_name'], 'class': 'whitespace_print'},
            {'name': self.format_value(aml['debit'], currency=cur, blank_if_zero=True), 'class': 'number'}, #{'name': self.format_value(cur._compute(self.env.user.company_id.currency_id, cur, aml['debit']), currency=cur, blank_if_zero=True), 'class': 'number'},
            {'name': self.format_value(aml['credit'], currency=cur, blank_if_zero=True), 'class': 'number'}, #{'name': self.format_value(cur._compute(self.env.user.company_id.currency_id, cur, aml['credit']), currency=cur, blank_if_zero=True), 'class': 'number'},
            {'name': self.format_value(cumulated_balance, currency=cur), 'class': 'number'}, #{'name': self.format_value(cur._compute(self.env.user.company_id.currency_id, cur, cumulated_balance), currency=cur), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            columns.insert(3,{'name': cur and self.format_value(aml['amount_currency'], currency=cur, blank_if_zero=True) or '', 'class': 'number'}) #currency
        return {
            'id': aml['id'],
            'caret_options': caret_type,
            'class': 'top-vertical-align',
            'parent_id': 'account_%d' % aml['account_id'],
            'name': aml['move_name'],
            'columns': columns,
            'level': 2,
        }
        #return super(ReportGeneralLedger, self)._get_aml_line(options, account, aml, cumulated_balance)'''

    @api.model
    def _get_query_sums(self, options_list, expanded_account=None):
        queries, params = super()._get_query_sums(options_list, expanded_account)
        #print('_get_query_sums-queries: ', queries)
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = self.env.user.company_id.currency_id
        if (cur.id != self.env.company.currency_id.id):
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
        print('_get_query_amls-query: ', query)
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = self.env.user.company_id.currency_id
        if (cur.id != self.env.company.currency_id.id):
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