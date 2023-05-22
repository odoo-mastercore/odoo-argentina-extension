# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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


class AccountReport(models.AbstractModel):
    _inherit = "account.report"

    filter_currencys = True

    
    @api.model
    def _get_options(self, previous_options=None):
        res = super(AccountReport, self)._get_options(previous_options)

        if self.filter_currencys :

            currencies = [] #self.env['res.currency'].search([])
            currencies.append(self.env.user.company_id.currency_id)
            currencies.append(self.env.user.company_id.foreign_currency_id)
            res['currenciess'] = [{'id': c.id, 'name': c.name, 'selected': False} for c in currencies]
            if 'curr' in self._context:
                for c in res['currenciess']:
                    if c['id'] == self._context.get('curr'):
                        c['selected'] = True
            else:
                for c in res['currenciess']:
                    if c['id'] == self.env.user.company_id.currency_id.id:
                        c['selected'] = True
            res['currencys'] = True
        return res


    def get_xlsx(self, options, response=None):
        for opt in options['currenciess']:
            if opt['selected'] and self.env['res.currency'].browse(opt['id']) != self.env.user.company_id.currency_id:
                return super(AccountReport, self.with_context(curr = opt['id'])).get_xlsx(options,response)
        return super(AccountReport, self).get_xlsx(options,response)

    
    def get_pdf(self, options):
        for opt in options['currenciess']:
            if opt['selected'] and self.env['res.currency'].browse(opt['id']) != self.env.user.company_id.currency_id:
                return super(AccountReport, self.with_context(curr = opt['id'])).get_pdf(options)
        return super(AccountReport, self).get_pdf(options)


class ReportAccountFinancialReport(models.Model):
    _inherit = "account.financial.html.report"

    """

    @api.model
    def _format_cell_value(self, financial_line, amount, currency=False, blank_if_zero=False):
        ''' Format the value to display inside a cell depending the 'figure_type' field in the financial report line.
        :param financial_line:  An account.financial.html.report.line record.
        :param amount:          A number.
        :param currency:        An optional res.currency record.
        :param blank_if_zero:   An optional flag forcing the string to be empty if amount is zero.
        :return:
        '''


        if not financial_line.formulas:
            return ''

        if self._context.get('no_format'):
            return amount
            
        if financial_line.figure_type == 'float':
            if 'curr' in self._context:
                cur = self.env['res.currency'].browse(self._context.get('curr'))
                
                return self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,amount),currency=cur, blank_if_zero=blank_if_zero)
            return super().format_value(amount, currency=currency, blank_if_zero=blank_if_zero)
        elif financial_line.figure_type == 'percents':
            return str(round(amount * 100, 1)) + '%'
        elif financial_line.figure_type == 'no_unit':
            return round(amount, 1)
        return amount

    """

    @api.model
    def _format_cell_value(self, financial_line, amount, currency=False, blank_if_zero=False):
        ''' Format the value to display inside a cell depending the 'figure_type' field in the financial report line.
        :param financial_line:  An account.financial.html.report.line record.
        :param amount:          A number.
        :param currency:        An optional res.currency record.
        :param blank_if_zero:   An optional flag forcing the string to be empty if amount is zero.
        :return:
        '''


        if not financial_line.formulas:
            return ''

        if self._context.get('no_format'):
            return amount
            
        if financial_line.figure_type == 'float':
            if 'curr' in self._context:
                cur = self.env['res.currency'].browse(self._context.get('curr'))
                
                return self.format_value(self.env.user.company_id.currency_id._convert_by_avg(amount, cur, self._context),currency=cur, blank_if_zero=blank_if_zero)
            return super().format_value(amount, currency=currency, blank_if_zero=blank_if_zero)
        elif financial_line.figure_type == 'percents':
            return str(round(amount * 100, 1)) + '%'
        elif financial_line.figure_type == 'no_unit':
            return round(amount, 1)
        return amount

class MulticurrencyRevaluationReport(models.Model):

    _inherit = 'account.multicurrency.revaluation'

    filter_currencys = False

    @api.model
    def _get_options(self, previous_options=None):
        res = super(MulticurrencyRevaluationReport, self)._get_options(previous_options)
        
        res.pop('currencys')
        return res

class ReportAgedPartner(models.AbstractModel):
    _inherit = "account.aged.partner"
    
    filter_currencys = True
      
    def _field_column(self, field_name, sortable=False, name=None, ellipsis=False, blank_if_zero=False):
        """Build a column based on a field.

        The type of the field determines how it is displayed.
        The column's title is the name of the field.
        :param field_name: The name of the fields.Field to use
        :param sortable: Allow the user to sort data based on this column
        :param name: Use a specific name for display.
        :param ellispsis (bool): The text displayed can be truncated in the web browser.
        :param blank_if_zero (bool): For numeric fields, do not display a value if it is equal to zero.
        :return (ColumnDetail): A usable column declaration to build the html
        """
        classes = ['text-nowrap']

        def getter(v):
            return self._fields[field_name].convert_to_cache(v.get(field_name, ''), self)
        if self._fields[field_name].type in ['float']:
            classes += ['number']
            def formatter(v):
                return v if v or not blank_if_zero else ''
        elif self._fields[field_name].type in ['monetary']:
            classes += ['number']
            def m_getter(v):
                return (v.get(field_name, ''), self.env['res.currency'].browse(
                    v.get(self._fields[field_name].currency_field, (False,))[0])
                )
            getter = m_getter

            def formatter(v):
                if 'curr' in self._context:
                    cur = self.env['res.currency'].browse(self._context.get('curr'))
                    return self.format_value(cur._compute(self.env.user.company_id.currency_id,cur,v[0]),currency=cur, blank_if_zero=blank_if_zero)
                return self.format_value(v[0], v[1], blank_if_zero=blank_if_zero)
        elif self._fields[field_name].type in ['char']:
            classes += ['text-center']
            def formatter(v): return v
        elif self._fields[field_name].type in ['date']:
            classes += ['date']
            def formatter(v): return format_date(self.env, v)
        elif self._fields[field_name].type in ['many2one']:
            classes += ['text-center']
            def r_getter(v):
                return v.get(field_name, False)
            getter = r_getter
            def formatter(v):
                return v[1] if v else ''

        IrModelFields = self.env['ir.model.fields']
        return self._custom_column(name=name or IrModelFields._get(self._name, field_name).field_description,
                                   getter=getter,
                                   formatter=formatter,
                                   classes=classes,
                                   ellipsis=ellipsis,
                                   sortable=sortable)


    @api.model
    def compute_format_value(self, amount, currency=False, blank_if_zero=False):
        ''' Format amount to have a monetary display (with a currency symbol).
        E.g: 1000 => 1000.0 $

        :param amount:          A number.
        :param currency:        An optional res.currency record.
        :param blank_if_zero:   An optional flag forcing the string to be empty if amount is zero.
        :return:                The formatted amount as a string.
        '''

        if 'curr' in self._context:
            cur = self.env['res.currency'].browse(self._context.get('curr'))
            return self.format_value(cur._compute(currency or self.env.company.currency_id,cur,amount),cur, blank_if_zero)

        return self.format_value(amount, currency, blank_if_zero)


    @api.model
    def _get_column_details(self, options):
        columns = [
            self._header_column(),
            self._field_column('report_date'),

            self._field_column('account_name', name=_("Account"), ellipsis=True),
            self._field_column('expected_pay_date'),
            self._field_column('period0', name=_("As of: %s", format_date(self.env, options['date']['date_to']))),
            self._field_column('period1', sortable=True),
            self._field_column('period2', sortable=True),
            self._field_column('period3', sortable=True),
            self._field_column('period4', sortable=True),
            self._field_column('period5', sortable=True),
            self._custom_column(  # Avoid doing twice the sub-select in the view
                name=_('Total'),
                classes=['number'],
                formatter=self.compute_format_value,
                getter=(lambda v: v['period0'] + v['period1'] + v['period2'] + v['period3'] + v['period4'] + v['period5']),
                sortable=True,
            ),
        ]

        if self.user_has_groups('base.group_multi_currency'):
            columns[2:2] = [
                self._field_column('amount_currency'),
                self._field_column('currency_id'),
            ]
        return columns

    

class Currency(models.Model):
    _inherit = "res.currency"


    def calculate_avg_rate(self, options,currency):
        avg_rate =0
        _logger.info('<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<,,')
        _logger.info(options)
        date_from = options['date_from']
        date_to = options['date_to']
        _logger.info('<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<,,')
        _logger.info(options)
        currency_rates = self.env['res.currency.rate'].search([('name','<=',date_to),('name','>=',date_from),('company_id','=',self.env.company.id),('currency_id','=',currency.id or False)]).mapped('company_rate')
        if currency_rates:
            avg_rate = sum(currency_rates)/ len(currency_rates) 
        return avg_rate



    def _convert_by_avg(self, from_amount, to_currency, options, round=True):
        """Returns the converted amount of ``from_amount``` from the currency
           ``self`` to the currency ``to_currency`` for the given ``date`` and
           company.

           :param company: The company from which we retrieve the convertion rate
           :param date: The nearest date from which we retriev the conversion rate.
           :param round: Round the result or not
        """
        self, to_currency = self or to_currency, to_currency or self
        assert self, "convert amount from unknown currency"
        assert to_currency, "convert amount to unknown currency"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount
        else:
            avg_rate = self.calculate_avg_rate(options, to_currency)
            _logger.info('average rate>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>.')
            _logger.info(avg_rate)
            to_amount = from_amount * avg_rate
        # apply rounding
        return to_currency.round(to_amount) if round else to_amount    