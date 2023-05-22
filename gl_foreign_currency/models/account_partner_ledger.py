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

    @api.model
    def _get_report_line_partner(self, options, partner, initial_balance, debit, credit, balance):
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = self.env.user.company_id.currency_id
        columns = [
            {'name': self.format_value(initial_balance,currency=cur), 'class': 'number'}, #{'name': self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,initial_balance),currency=cur), 'class': 'number'},
            {'name': self.format_value(debit,currency=cur), 'class': 'number'}, #{'name': self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,debit),currency=cur), 'class': 'number'},
            {'name': self.format_value(credit,currency=cur), 'class': 'number'}, #{'name': self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,credit),currency=cur), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            columns.append({'name': ''})
        columns.append({'name': self.format_value(balance,currency=cur), 'class': 'number'})#columns.append({'name': self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,balance),currency=cur), 'class': 'number'})
        unfold_all = self._context.get('print_mode') and not options.get('unfolded_lines')
        return {
            'id': 'partner_%s' % (partner.id if partner else 0),
            'partner_id': partner.id if partner else None,
            'name': partner is not None and (partner.name or '')[:128] or _('Unknown Partner'),
            'columns': columns,
            'level': 2,
            'trust': partner.trust if partner else None,
            'unfoldable': not cur.is_zero(debit) or not cur.is_zero(credit),
            'unfolded': 'partner_%s' % (partner.id if partner else 0) in options['unfolded_lines'] or unfold_all,
            'colspan': 6,
        }
        return super(ReportPartnerLedger, self)._get_report_line_partner(options, partner, initial_balance, debit, credit, balance)

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        #print('_dynamic_lines_generator-self: ', self)
        #print('_dynamic_lines_generator-report: ', report)
        #print('_dynamic_lines_generator-options: ', options)
        #print('_dynamic_lines_generator-all_column_groups_expression_totals: ', all_column_groups_expression_totals)
        if self.env.context.get('print_mode') and options.get('filter_search_bar'):
            # Handled here instead of in custom options initializer as init_options functions aren't re-called when printing the report.
            options.setdefault('forced_domain', []).append(('partner_id', 'ilike', options['filter_search_bar']))

        partner_lines, totals_by_column_group = self._build_partner_lines(report, options)
        #print('_dynamic_lines_generator-_build_partner_lines-partner_lines: ', partner_lines)
        #print('_dynamic_lines_generator-_build_partner_lines-totals_by_column_group: ', totals_by_column_group)
        lines = report._regroup_lines_by_name_prefix(options, partner_lines, '_report_expand_unfoldable_line_partner_ledger_prefix_group', 0)
        #print('_dynamic_lines_generator-_regroup_lines_by_name_prefix-lines: ', lines)
        # Inject sequence on dynamic lines
        lines = [(0, line) for line in lines]

        # Report total line.
        lines.append((0, self._get_report_line_total(options, totals_by_column_group)))

        return lines

    '''@api.model
    def _get_report_line_total(self, options, initial_balance, debit, credit, balance):
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = self.env.user.company_id.currency_id
        columns = [
            {'name': self.format_value(initial_balance,currency=cur), 'class': 'number'}, #{'name': self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,initial_balance),currency=cur), 'class': 'number'},
            {'name': self.format_value(debit,currency=cur), 'class': 'number'}, #{'name': self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,debit),currency=cur), 'class': 'number'},
            {'name': self.format_value(credit,currency=cur), 'class': 'number'}, #{'name': self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,credit),currency=cur), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            columns.append({'name': ''})
        columns.append({'name': self.format_value(balance,currency=cur), 'class': 'number'}) #columns.append({'name': self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,balance),currency=cur), 'class': 'number'})
        return {
            'id': 'partner_ledger_total_%s' % self.env.company.id,
            'name': _('Total'),
            'class': 'total',
            'level': 1,
            'columns': columns,
            'colspan': 6,
        }

        return super(ReportPartnerLedger, self)._get_report_line_total(options, initial_balance, debit, credit, balance)'''

    '''@api.model
    def _do_query(self, options, expanded_partner=None):
        #print('_do_query-self: ', self)
        #print('_do_query-options: ', options)
        def assign_sum(row):
            key = row['key']
            fields = ['balance', 'debit', 'credit'] if key == 'sum' else ['balance']
            if any(not company_currency.is_zero(row[field]) for field in fields):
                amount = defaultdict(lambda: defaultdict(float))
                groupby_partners.setdefault(row['groupby'], amount)
                for field in fields:
                    groupby_partners[row['groupby']][key][field] += row[field]

        company_currency = self.env.company.currency_id
        # flush the tables that gonna be queried
        self.env['account.move.line'].flush(fnames=self.env['account.move.line']._fields)
        self.env['account.move'].flush(fnames=self.env['account.move']._fields)
        self.env['account.partial.reconcile'].flush(fnames=self.env['account.partial.reconcile']._fields)

        # Execute the queries and dispatch the results.
        query, params = self._get_query_sums(options) #, expanded_partner=expanded_partner
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = self.env.user.company_id.currency_id
        #print('_do_query-cur: ', cur)
        if (cur.id != self.env.company.currency_id.id):
            #print('_do_query-cur!=: ', cur)
            #print('_do_query-find: ', query.find('FROM "account_move_line" LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")'))
            if (query.find('FROM "account_move_line" LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")') > 0):
                query = query.replace('SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit', 'SUM(ROUND(account_move_line.debit / ROUND((1/currency_rate.rate),4), 2)) AS debit')
                query = query.replace('SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit', 'SUM(ROUND(account_move_line.credit / ROUND((1/currency_rate.rate),4), 2)) AS credit')
                query = query.replace('SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance', 'SUM(ROUND(account_move_line.balance / ROUND((1/currency_rate.rate),4), 2)) AS balance')
                query = query.replace('FROM "account_move_line" LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")', 'FROM "account_move_line" LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name") INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id") LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id") LEFT JOIN account_journal journal ON (journal.id = account_move_line.journal_id) ')
                query = query.replace('GROUP BY account_move_line.partner_id', ' AND (journal.exclude_report is NULL or journal.exclude_report = False) GROUP BY account_move_line.partner_id')
        else:
            if (query.find('FROM "account_move_line" LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")') > 0):
                query = query.replace('FROM "account_move_line" LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")', 'FROM "account_move_line" LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id") LEFT JOIN account_journal journal ON (journal.id = account_move_line.journal_id) ')
                query = query.replace('GROUP BY account_move_line.partner_id', ' AND (journal.exclude_report is NULL or journal.exclude_report = False) GROUP BY account_move_line.partner_id')

        #print('_do_query-query: ', query)
        #print('_do_query-params: ', params)
        groupby_partners = {}

        self._cr.execute(query, params)
        for res in self._cr.dictfetchall():
            assign_sum(res)

        # Fetch the lines of unfolded accounts.
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])
        if expanded_partner or unfold_all or options['unfolded_lines']:
            query, params = self._get_query_amls(options, expanded_partner=expanded_partner)
            #print('_get_query_amls-query: ', query)
            #print('_get_query_amls-params: ', params)
            if (cur.id != self.env.company.currency_id.id):
                if (query.find('FROM "account_move_line" LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")') > 0):
                    query = query.replace('account_move_line.amount_currency,', 'ROUND(COALESCE((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 2) ELSE account_move_line.amount_currency END) / (ROUND((1/currency_rate.rate),4)), 0.0), 2) AS amount_currency,')
                    query = query.replace('account_move_line__move_id.name         AS move_name,', 'account_move_line__move_id.name         AS move_name, (select count(distinct am.id) FROM account_move_line aml LEFT JOIN account_move am ON (aml.move_id = am.id) where am.name = account_move_line__move_id.name ) AS count_move_name,')
                    query = query.replace('ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,','ROUND(ROUND((account_move_line.debit / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision)   AS debit,')
                    query = query.replace('ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,','ROUND(ROUND((account_move_line.credit / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision)  AS credit,')
                    query = query.replace('ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,','ROUND(ROUND((account_move_line.balance / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision) AS balance,')
                    query = query.replace('FROM "account_move_line" LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")', 'FROM "account_move_line" LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name") INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id") LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")')
                    query = query.replace('ORDER BY account_move_line.date, account_move_line.id', ' AND (journal.exclude_report is NULL or journal.exclude_report = False) ORDER BY account_move_line.date, account_move_line.id')
            else:
                if (query.find('FROM "account_move_line" LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")') > 0):
                    query = query.replace('account_move_line.amount_currency,', 'ROUND(COALESCE((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 2) ELSE account_move_line.amount_currency END), 0.0), 2) AS amount_currency,')
                    query = query.replace('account_move_line__move_id.name         AS move_name,', 'account_move_line__move_id.name         AS move_name, (select count(distinct am.id) FROM account_move_line aml LEFT JOIN account_move am ON (aml.move_id = am.id) where am.name = account_move_line__move_id.name ) AS count_move_name,')
                    query = query.replace('FROM "account_move_line" LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")', 'FROM "account_move_line" LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name") INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id") LEFT JOIN "account_move" AS "account_move_line__move_id" ON ("account_move_line"."move_id" = "account_move_line__move_id"."id")')
                    query = query.replace('ORDER BY account_move_line.date, account_move_line.id', ' AND (journal.exclude_report is NULL or journal.exclude_report = False) ORDER BY account_move_line.date, account_move_line.id')
            #print('_get_query_amls-query: ', query)
            #print('_get_query_amls-params: ', params)
            self._cr.execute(query, params)
            for res in self._cr.dictfetchall():
                if res['partner_id'] not in groupby_partners:
                    continue
                groupby_partners[res['partner_id']].setdefault('lines', [])
                groupby_partners[res['partner_id']]['lines'].append(res)

            query, params = self._get_lines_without_partner(options, expanded_partner=expanded_partner)
            self._cr.execute(query, params)
            for row in self._cr.dictfetchall():
                # don't show lines of partners not expanded
                if row['partner_id'] in groupby_partners:
                    groupby_partners[row['partner_id']].setdefault('lines', [])
                    row['class'] = ' text-muted'
                    groupby_partners[row['partner_id']]['lines'].append(row)
                if None in groupby_partners:
                    # reconciled lines without partners are fetched to be displayed under the matched partner
                    # and thus but be inversed to be displayed under the unknown partner
                    none_row = row.copy()
                    none_row['class'] = ' text-muted'
                    none_row['debit'] = row['credit']
                    none_row['credit'] = row['debit']
                    none_row['balance'] = -row['balance']
                    groupby_partners[None].setdefault('lines', [])
                    groupby_partners[None]['lines'].append(none_row)

        # correct the sums per partner, for the lines without partner reconciled with a line having a partner
        query, params = self._get_sums_without_partner(options) #, expanded_partner=expanded_partner
        self._cr.execute(query, params)
        total = total_debit = total_credit = total_initial_balance = 0
        for row in self._cr.dictfetchall():
            key = row['key']
            total_debit += key == 'sum' and row['debit'] or 0
            total_credit += key == 'sum' and row['credit'] or 0
            total_initial_balance += key == 'initial_balance' and row['balance'] or 0
            total += key == 'sum' and row['balance'] or 0
            if None not in groupby_partners and not (expanded_partner or unfold_all or options['unfolded_lines']):
                groupby_partners.setdefault(None, {})
            if row['groupby'] not in groupby_partners:
                continue
            assign_sum(row)

        if None in groupby_partners:
            if 'sum' not in groupby_partners[None]:
                groupby_partners[None].setdefault('sum', {'debit': 0, 'credit': 0, 'balance': 0})
            if 'initial_balance' not in groupby_partners[None]:
                groupby_partners[None].setdefault('initial_balance', {'balance': 0})
            #debit/credit are inversed for the unknown partner as the computation is made regarding the balance of the known partner
            groupby_partners[None]['sum']['debit'] += total_credit
            groupby_partners[None]['sum']['credit'] += total_debit
            groupby_partners[None]['sum']['balance'] -= total
            groupby_partners[None]['initial_balance']['balance'] -= total_initial_balance

        # Retrieve the partners to browse.
        # groupby_partners.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        # Note a search is done instead of a browse to preserve the table ordering.
        if expanded_partner:
            partners = expanded_partner
        elif groupby_partners:
            partners = self.env['res.partner'].with_context(active_test=False).search([('id', 'in', list(groupby_partners.keys()))])
        else:
            partners = []

        # Add 'Partner Unknown' if needed
        if None in groupby_partners.keys():
            partners = [p for p in partners] + [None]
        return [(partner, groupby_partners[partner.id if partner else None]) for partner in partners]
'''
    @api.model
    def _load_more_lines(self, options, line_id, offset, load_more_remaining, progress):
        ''' Get lines for an expanded line using the load more.
        :param options: The report options.
        :return:        A list of lines, each one represented by a dictionary.
        '''
        #print('_load_more_lines-self: ', self)
        lines = []
        expanded_partner = line_id and self.env['res.partner'].browse(int(line_id[9:]))

        load_more_counter = self.MAX_LINES

        starting_offset = offset
        starting_load_more_counter = load_more_counter

        # Fetch the next batch of lines
        amls_query, amls_params = self._get_query_amls(options, expanded_partner=expanded_partner, offset=offset, limit=load_more_counter)
        self._cr.execute(amls_query, amls_params)
        for aml in self._cr.dictfetchall():
            # Don't show more line than load_more_counter.
            if load_more_counter == 0:
                break

            cumulated_init_balance = progress
            progress += aml['balance']

            # account.move.line record line.
            lines.append(self._get_report_line_move_line(options, expanded_partner, aml, cumulated_init_balance, progress))

            offset += 1
            load_more_remaining -= 1
            load_more_counter -= 1

        query, params = self._get_lines_without_partner(options, expanded_partner=expanded_partner, offset=offset-starting_offset, limit=starting_load_more_counter-load_more_counter)
        self._cr.execute(query, params)
        for row in self._cr.dictfetchall():
            # Don't show more line than load_more_counter.
            if load_more_counter == 0:
                break

            row['class'] = ' text-muted'
            if line_id == 'loadmore_0':
                # reconciled lines without partners are fetched to be displayed under the matched partner
                # and thus but be inversed to be displayed under the unknown partner
                row['debit'] = row['balance'] < 0 and row['credit'] or 0
                row['credit'] = row['balance'] > 0 and row['debit'] or 0
                row['balance'] = -row['balance']
            cumulated_init_balance = progress
            progress += row['balance']
            lines.append(self._get_report_line_move_line(options, expanded_partner, row, cumulated_init_balance, progress))

            offset += 1
            load_more_remaining -= 1
            load_more_counter -= 1

        if load_more_remaining > 0:
            # Load more line.
            lines.append(self._get_report_line_load_more(
                options,
                expanded_partner,
                offset,
                load_more_remaining,
                progress,
            ))
        return lines

    @api.model
    def _get_partner_ledger_lines(self, options, line_id=None):
        ''' Get lines for the whole report or for a specific line.
        :param options: The report options.
        :return:        A list of lines, each one represented by a dictionary.
        '''
        #print('_get_partner_ledger_lines-self: ', self)
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = self.env.user.company_id.currency_id
        #print('_get_partner_ledger_lines-cur: ', cur)
        lines = []
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])
        #print('_get_partner_ledger_lines-unfold_all: ', unfold_all)
        expanded_partner = line_id and self.env['res.partner'].browse(int(line_id[8:]))
        #print('_get_partner_ledger_lines-expanded_partner: ', expanded_partner)
        partners_results = self._do_query(options, expanded_partner=expanded_partner)
        #print('_get_partner_ledger_lines-partners_results: ', partners_results)

        total_initial_balance = total_debit = total_credit = total_balance = 0.0
        for partner, results in partners_results:
            is_unfolded = 'partner_%s' % (partner.id if partner else 0) in options['unfolded_lines']

            # res.partner record line.
            partner_sum = results.get('sum', {})
            partner_init_bal = results.get('initial_balance', {})

            initial_balance = partner_init_bal.get('balance', 0.0)
            debit = partner_sum.get('debit', 0.0)
            credit = partner_sum.get('credit', 0.0)
            balance = initial_balance + partner_sum.get('balance', 0.0)

            lines.append(self._get_report_line_partner(options, partner, initial_balance, debit, credit, balance))

            total_initial_balance += initial_balance
            total_debit += debit
            total_credit += credit
            total_balance += balance
            if unfold_all or is_unfolded:
                cumulated_balance = initial_balance

                # account.move.line record lines.
                amls = results.get('lines', [])

                load_more_remaining = len(amls)
                load_more_counter = self._context.get('print_mode') and load_more_remaining or self.MAX_LINES
                count_move_name = 0
                gp_amount_currency = 0
                gp_debit = 0
                gp_credit = 0
                gp_balance = 0
                gp_cumulated_init_balance = 0
                gp_cumulated_balance = 0
                for aml in amls:
                    # Don't show more line than load_more_counter.
                    if load_more_counter == 0:
                        break

                    cumulated_init_balance = cumulated_balance
                    cumulated_balance += aml['balance']
                    if (aml['count_move_name'] == 1):
                        count_move_name = 0
                        gp_amount_currency = 0
                        gp_debit = 0
                        gp_credit = 0
                        gp_balance = 0
                    else:
                        count_move_name = count_move_name + 1
                        gp_amount_currency = gp_amount_currency + aml['amount_currency']
                        gp_debit = gp_debit + aml['debit']
                        gp_credit = gp_credit + aml['credit']
                        gp_balance = gp_balance + aml['balance']
                        aml['journal_code'] = 'GdP'
                        aml['amount_currency'] = gp_amount_currency
                        aml['debit'] = gp_debit
                        aml['credit'] = gp_credit
                        aml['balance'] = gp_balance
                        cumulated_init_balance = gp_cumulated_init_balance
                        cumulated_balance = gp_cumulated_init_balance - gp_credit
                    if (aml['count_move_name'] == count_move_name) or aml['count_move_name'] == 1:
                        lines.append(self._get_report_line_move_line(options, partner, aml, cumulated_init_balance, cumulated_balance))
                        count_move_name = 0
                        gp_amount_currency = 0
                        gp_debit = 0
                        gp_credit = 0
                        gp_balance = 0
                        gp_cumulated_init_balance = 0
                        gp_cumulated_balance = 0
                        gp_cumulated_init_balance = cumulated_balance

                    load_more_remaining -= 1
                    load_more_counter -= 1

                if load_more_remaining > 0:
                    # Load more line.
                    lines.append(self._get_report_line_load_more(
                        options,
                        partner,
                        self.MAX_LINES,
                        load_more_remaining,
                        cumulated_balance,
                    ))
                    #print('_get_partner_ledger_lines-lines: ', lines)

        if not line_id:
            # Report total line.
            lines.append(self._get_report_line_total(
                options,
                total_initial_balance,
                total_debit,
                total_credit,
                total_balance
            ))
        return lines

    '''@api.model
    def _get_report_line_move_line(self, options, partner, aml, cumulated_init_balance, cumulated_balance):
        #print('_get_report_line_move_line-self: ', self)
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = self.env.user.company_id.currency_id
        if aml['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move'

        date_maturity = aml['date_maturity'] and format_date(self.env, fields.Date.from_string(aml['date_maturity']))
        columns = [
            {'name': aml['journal_code']},
            {'name': aml['account_code']},
            {'name': aml['move_name'] if aml['payment_id'] else self._format_aml_name(aml['name'], aml['ref'], aml['move_name']), 'class': 'o_account_report_line_ellipsis'},
            {'name': date_maturity or '', 'class': 'date'},
            {'name': aml['matching_number'] or ''},
            {'name': self.format_value(cumulated_init_balance,currency=cur), 'class': 'number'}, #{'name': self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,cumulated_init_balance),currency=cur), 'class': 'number'},
            {'name': self.format_value(aml['debit'],currency=cur, blank_if_zero=True), 'class': 'number'}, #{'name': self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,aml['debit']),currency=cur, blank_if_zero=True), 'class': 'number'},
            {'name': self.format_value(aml['credit'],currency=cur, blank_if_zero=True), 'class': 'number'}, #{'name': self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,aml['credit']),currency=cur, blank_if_zero=True), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            if aml['currency_id']:
                currency = self.env['res.currency'].browse(aml['currency_id'])
                formatted_amount = self.format_value(aml['amount_currency'], currency=cur, blank_if_zero=True)
                columns.append({'name': formatted_amount, 'class': 'number'})
            else:
                columns.append({'name': ''})
        columns.append({'name': self.format_value(cumulated_balance,currency=cur), 'class': 'number'}) #columns.append({'name': self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,cumulated_balance),currency=cur), 'class': 'number'})
        return {
            'id': aml['id'],
            'parent_id': 'partner_%s' % (partner.id if partner else 0),
            'name': format_date(self.env, aml['date']),
            'class': 'text' + aml.get('class', ''),  # do not format as date to prevent text centering
            'columns': columns,
            'caret_options': caret_type,
            'level': 2,
        }

        return super(ReportPartnerLedger, self)._get_report_line_move_line(options, partner, aml, cumulated_init_balance, cumulated_balance)
'''
    def _get_query_sums(self, options):
        #print('_get_query_sums===> ', self)
        query, params = super()._get_query_sums(options)
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = self.env.user.company_id.currency_id
        if (cur.id != self.env.company.currency_id.id):
            if (query.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")') > 0):
                query = query.replace('SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit', 'SUM(ROUND(account_move_line.debit / ROUND((1/currency_rate.rate),4), 2)) AS debit')
                query = query.replace('SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit', 'SUM(ROUND(account_move_line.credit / ROUND((1/currency_rate.rate),4), 2)) AS credit')
                query = query.replace('SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance', 'SUM(ROUND(account_move_line.balance / ROUND((1/currency_rate.rate),4), 2)) AS balance')
                query = query.replace('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")', 'FROM "account_move_line" LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name") INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id") LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id") LEFT JOIN account_journal journal ON (journal.id = account_move_line.journal_id) ')
                query = query.replace('GROUP BY account_move_line.partner_id', ' AND (journal.exclude_report is NULL or journal.exclude_report = False) GROUP BY account_move_line.partner_id')
        else:
            #print('_get_query_sums-else===> ', self)
            if (query.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")') > 0):
                query = query.replace('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")', 'FROM "account_move_line" LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name") INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id") LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id") LEFT JOIN account_journal journal ON (journal.id = account_move_line.journal_id) ')
                query = query.replace('GROUP BY account_move_line.partner_id', ' AND (journal.exclude_report is NULL or journal.exclude_report = False) GROUP BY account_move_line.partner_id')
                #print('_get_query_sums-modif===> ', self)
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
        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
        else:
            cur = self.env.user.company_id.currency_id
        if (cur.id != self.env.company.currency_id.id):
            if (query.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")') > 0):
                query = query.replace('account_move_line.amount_currency,', 'ROUND(COALESCE((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 2) ELSE account_move_line.amount_currency END) / (ROUND((1/currency_rate.rate),4)), 0.0), 2) AS amount_currency,')
                query = query.replace('account_move.name                                                                AS move_name,', 'account_move.name         AS move_name, (select count(distinct am.id) FROM account_move_line aml LEFT JOIN account_move am ON (aml.move_id = am.id) where am.name = account_move.name ) AS count_move_name,')
                query = query.replace('account_move.name                                                                   AS move_name,', 'account_move.name         AS move_name, (select count(distinct am.id) FROM account_move_line aml LEFT JOIN account_move am ON (aml.move_id = am.id) where am.name = account_move.name ) AS count_move_name,')
                query = query.replace('ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,','ROUND(ROUND((account_move_line.debit / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision)   AS debit,')
                query = query.replace('ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,','ROUND(ROUND((account_move_line.credit / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision)  AS credit,')
                query = query.replace('ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,','ROUND(ROUND((account_move_line.balance / ROUND((1/currency_rate.rate),4)), 2) * currency_table.rate, currency_table.precision) AS balance,')
                query = query.replace('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")', 'FROM "account_move_line" LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name") INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id") LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")')
                query = query.replace('ORDER BY account_move_line.date, account_move_line.id', ' AND (journal.exclude_report is NULL or journal.exclude_report = False) ORDER BY account_move_line.date, account_move_line.id')
        else:
            if (query.find('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")') > 0):
                query = query.replace('account_move_line.amount_currency,', 'ROUND(COALESCE((CASE WHEN account_move_line.currency_id=currency_rate.currency_id THEN ROUND(account_move_line.amount_currency * ROUND((1/currency_rate.rate),4), 2) ELSE account_move_line.amount_currency END), 0.0), 2) AS amount_currency,')
                query = query.replace('account_move.name                                                                AS move_name,', 'account_move.name         AS move_name, (select count(distinct am.id) FROM account_move_line aml LEFT JOIN account_move am ON (aml.move_id = am.id) where am.name = account_move.name ) AS count_move_name,')
                query = query.replace('account_move.name                                                                   AS move_name,', 'account_move.name         AS move_name, (select count(distinct am.id) FROM account_move_line aml LEFT JOIN account_move am ON (aml.move_id = am.id) where am.name = account_move.name ) AS count_move_name,')
                query = query.replace('FROM "account_move_line" LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")', 'FROM "account_move_line" LEFT JOIN "res_currency_rate" as "currency_rate" ON ("account_move_line"."date" = "currency_rate"."name") INNER JOIN "res_company" as "company_rate" ON ("account_move_line"."company_id" = "company_rate"."id" AND "company_rate"."foreign_currency_id" = "currency_rate"."currency_id") LEFT JOIN "account_account" AS "account_move_line__account_id" ON ("account_move_line"."account_id" = "account_move_line__account_id"."id")')
                query = query.replace('ORDER BY account_move_line.date, account_move_line.id', ' AND (journal.exclude_report is NULL or journal.exclude_report = False) ORDER BY account_move_line.date, account_move_line.id')
        #print('_get_query_amls-query: ', query)
        #print('_get_query_amls-all_params: ', all_params)

        self._cr.execute(query, all_params)
        for aml_result in self._cr.dictfetchall():
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
        for result in aml_results:
            #print('_report_expand_unfoldable_line_partner_ledger-result===> ', result)
            if not self._context.get('print_mode') and report.load_more_limit and treated_results_count == report.load_more_limit:
                # We loaded one more than the limit on purpose: this way we know we need a "load more" line
                has_more = True
                break
            #print('_report_expand_unfoldable_line_partner_ledger-options===> ', options)
            #print('_report_expand_unfoldable_line_partner_ledger-line_dict_id===> ', line_dict_id)
            #print('_report_expand_unfoldable_line_partner_ledger-next_progress===> ', next_progress)
            #print('_report_expand_unfoldable_line_partner_ledger-level_shift===> ', level_shift)
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
            #print('col_expr_label: ', col_expr_label)
            if col_expr_label == 'ref':
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