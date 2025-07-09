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
from odoo.tools import SQL


try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter
import io
import logging
_logger = logging.getLogger(__name__)

class PartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = "account.partner.ledger.report.handler"
    
    filter_account_acc = True


    def _get_custom_display_config(self):
        res = super(PartnerLedgerCustomHandler, self)._get_custom_display_config()
        #método se ejecuta al entrar
        #_logger.warning(f'Registro: {res}')
        #_logger.warning(f'Registro _get_custom_display_config: {res}')
        return res

    # def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
    #     res = super(PartnerLedgerCustomHandler, self)._dynamic_lines_generator(report, options, all_column_groups_expression_totals, warnings=None)
    #     #método se ejecuta al entrar
    #     #_logger.warning(f'Registro: {res}')
    #     #_logger.warning(f'Registro _dynamic_lines_generator: {res}')
    #     return res
    
    # def _build_partner_lines(self, report, options, level_shift=0):
    #     res = super(PartnerLedgerCustomHandler, self)._build_partner_lines(report, options, level_shift)
    #     #método se ejecuta al entrar
    #     #_logger.warning(f'Registro: {res}')
    #     #_logger.warning(f'Registro _build_partner_lines: {res}')
    #     return res
    

    def _custom_options_initializer(self, report, options, previous_options):
        res = super(PartnerLedgerCustomHandler, self)._custom_options_initializer(report, options, previous_options)
        #método se ejecuta al entrar
        #_logger.warning(f'Registro _custom_options_initializer: {res}')
        return res
    
    def _custom_unfold_all_batch_data_generator(self, report, options, lines_to_expand_by_function):
        res = super(PartnerLedgerCustomHandler, self)._custom_unfold_all_batch_data_generator(report, options, lines_to_expand_by_function)
        #se ejecuta cuando se aplica el filtro de de diarios en borrador diarios desconciliados
        #_logger.warning(f'Registro _custom_unfold_all_batch_data_generator: {res}')
        return res
    
    
    # def _query_partners(self, report, options):
    #     res = super(PartnerLedgerCustomHandler, self)._query_partners(report, options)
    #     #método se ejecuta al entrar
    #     #_logger.warning(f'_query_partners: {res}')
    #     return res

    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        res = super(PartnerLedgerCustomHandler, self)._get_aml_values(options, partner_ids, offset, limit)
        _logger.warning(f'resultado: {res}')
        return res
    #viene de la 15.0
    def _get_query_sums(self, report, options) -> SQL:
        super(PartnerLedgerCustomHandler, self)._get_query_sums(report, options)
        #método se ejecuta al entrar
        _logger.warning(f'Reportes: {report}')
        #_logger.warning(f'options: {options}')
        #_logger.warning(f'ITEMS: {report._split_options_per_column_group(options).items()}')
        #_logger.warning(f'_get_query_sums: {res}')
        """ Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all partners.
        - sums for the initial balances.
        :param options:             The report options.
        :return:                    query as SQL object
        """
        queries = []
        account_acc_ids = []
        if ('account_acc_ids' in options and len(options['account_acc_ids']) > 0):
            account_acc_ids = options['account_acc_ids']
        if ('account_acc_ids' in self._context and len(self._context.get('account_acc_ids')) > 0):
            account_acc_ids = self._context.get('account_acc_ids')
        #where_aditional = ("AND account_move_line.account_id IN " + str(account_acc_ids).replace('[', '(').replace(']', ')') if (len(account_acc_ids) > 0) else "AND account_move_line.account_id IS NOT NULL")
        if len(account_acc_ids) > 0:
            # Asegúrate de que los IDs sean enteros para evitar inyección SQL
            account_ids_str = ','.join(map(str, account_acc_ids))
            where_aditional_sql = f"account_move_line.account_id IN ({account_ids_str})"
        else:
            where_aditional_sql = "account_move_line.account_id IS NOT NULL"
        # Create the currency table.
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(column_group_options, 'from_beginning')
            query.add_where(SQL(where_aditional_sql))
            date_from = options['date']['date_from']
            queries.append(SQL(
                """
                (WITH partner_sums AS (
                    SELECT
                        account_move_line.partner_id            AS groupby,
                        %(column_group_key)s                    AS column_group_key,
                        SUM(%(debit_select)s)                   AS debit,
                        SUM(%(credit_select)s)                  AS credit,
                        SUM(%(balance_select)s)                 AS amount,
                        SUM(%(balance_select)s)                 AS balance,
                        BOOL_AND(account_move_line.reconciled)  AS all_reconciled,
                        MAX(account_move_line.date)             AS latest_date
                    FROM %(table_references)s %(currency_table_join)s
                    WHERE %(search_condition)s
                    GROUP BY account_move_line.partner_id
                )
                SELECT *
                FROM partner_sums
                WHERE partner_sums.balance != 0
                OR partner_sums.all_reconciled = FALSE
                OR partner_sums.latest_date >= %(date_from)s
                )""",
                column_group_key=column_group_key,
                debit_select=report._currency_table_apply_rate(SQL("account_move_line.debit")),
                credit_select=report._currency_table_apply_rate(SQL("account_move_line.credit")),
                balance_select=report._currency_table_apply_rate(SQL("account_move_line.balance")),
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join_for_leader_partner(column_group_options),
                search_condition = query.where_clause,
                date_from=date_from,
            ))
        _logger.warning(f'_clause: {queries}')
        return SQL(' UNION ALL ').join(queries)

    def _get_initial_balance_values(self, partner_ids, options):
        res = super(PartnerLedgerCustomHandler, self)._get_initial_balance_values(partner_ids, options)
        #se ejecuta cuando se aplica cualquier filtro de los 5 primeros y al entrar al reporte
        #_logger.warning(f'_get_initial_balance_values: {res}')
        return res

    def _get_options_initial_balance(self, options):
        res = super(PartnerLedgerCustomHandler, self)._get_options_initial_balance(options)
        #se ejecuta cuando se aplica el filtro de de diarios en borrador diarios desconciliados
        #_logger.warning(f'_get_options_initial_balance: {res}')
        return res 

    #viene de la version 15.0
    def _get_sums_without_partner(self, options):
        #método se ejecuta al entrar
        _logger.warning(f'_get_sums_without_partner: ')
        account_acc_ids = []
        if ('account_acc_ids' in options and len(options['account_acc_ids']) > 0):
            account_acc_ids = options['account_acc_ids']
        if ('account_acc_ids' in self._context and len(self._context.get('account_acc_ids')) > 0):
            account_acc_ids = self._context.get('account_acc_ids')
        #where_aditional = (" OR account_move_line.account_id IN " + str(account_acc_ids).replace('[', '(').replace(']', ')') if (len(account_acc_ids) > 0) else "")
        if len(account_acc_ids) > 0:
            # Asegúrate de que los IDs sean enteros para evitar inyección SQL
            account_ids_str = ','.join(map(str, account_acc_ids))
            where_aditional_sql = f"account_move_line.account_id IN ({account_ids_str})"
        else:
            where_aditional_sql = "account_move_line.account_id IS NOT NULL"
        
        """ Get the sum of lines without partner reconciled with a line with a partner, grouped by partner. Those lines
        should be considered as belonging to the partner for the reconciled amount as it may clear some of the partner
        invoice/bill and they have to be accounted in the partner balance."""
        queries = []
        report = self.env.ref('account_reports.partner_ledger_report')
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query = report._get_report_query(column_group_options, 'from_beginning')
            query.add_where(SQL(where_aditional_sql))
            queries.append(SQL(
                """
                SELECT
                    %(column_group_key)s        AS column_group_key,
                    aml_with_partner.partner_id AS groupby,
                    SUM(%(debit_select)s)       AS debit,
                    SUM(%(credit_select)s)      AS credit,
                    SUM(%(balance_select)s)     AS amount,
                    SUM(%(balance_select)s)     AS balance
                FROM %(table_references)s
                JOIN account_partial_reconcile partial
                    ON account_move_line.id = partial.debit_move_id OR account_move_line.id = partial.credit_move_id
                JOIN account_move_line aml_with_partner ON
                    (aml_with_partner.id = partial.debit_move_id OR aml_with_partner.id = partial.credit_move_id)
                    AND aml_with_partner.partner_id IS NOT NULL
                %(currency_table_join)s
                WHERE partial.max_date <= %(date_to)s AND %(search_condition)s
                    AND account_move_line.partner_id IS NULL  
                GROUP BY aml_with_partner.partner_id
                """,
                column_group_key=column_group_key,
                debit_select=report._currency_table_apply_rate(SQL("CASE WHEN aml_with_partner.balance > 0 THEN 0 ELSE partial.amount END")),
                credit_select=report._currency_table_apply_rate(SQL("CASE WHEN aml_with_partner.balance < 0 THEN 0 ELSE partial.amount END")),
                balance_select=report._currency_table_apply_rate(SQL("-SIGN(aml_with_partner.balance) * partial.amount")),
                table_references=query.from_clause,
                currency_table_join=report._currency_table_aml_join_for_leader_partner(column_group_options, aml_alias=SQL("aml_with_partner")),
                date_to=column_group_options['date']['date_to'],
                search_condition = query.where_clause#query.add_where(SQL(where_aditional)),
            ))

        return SQL(" UNION ALL ").join(queries)

    # def _report_expand_unfoldable_line_partner_ledger(self, line_dict_id, groupby, options, progress, offset, unfold_all_batch_data=None):
    #     res = super(PartnerLedgerCustomHandler, self)._report_expand_unfoldable_line_partner_ledger(line_dict_id, groupby, options, progress, offset, unfold_all_batch_data)
    #     _logger.warning(f'_report_expand_unfoldable_line_partner_ledger: {res}')
    #     return res
    
    def _init_load_more_progress(self, options, line_dict):
        res = super(PartnerLedgerCustomHandler, self)._init_load_more_progress(options, line_dict)
         #se ejecuta cuando se desplega uno de los campos del reporte
        #_logger.warning(f'_init_load_more_progress: {res}')
        return res

    def _get_partner_aml_report_lines(self, report, options, partner_line_id, aml_results, progress, offset=0, level_shift=0):
        res = super(PartnerLedgerCustomHandler, self)._get_partner_aml_report_lines(report, options, partner_line_id, aml_results, progress, offset, level_shift)
        #se ejecuta cuando se aplica el filtro Report o Reporte
        #_logger.warning(f'_get_partner_aml_report_lines: {res}')
        return res 

    # def _is_report_limit_reached(self, report, options, results_count):
    #     res = super(PartnerLedgerCustomHandler)._is_report_limit_reached(report, options, results_count)
    #     _logger.warning(f'_is_report_limit_reached: {res}')
    #     return res
    
    def _get_additional_column_aml_values(self):
        res = super(PartnerLedgerCustomHandler, self)._get_additional_column_aml_values()
        #se ejecuta cuando se desplega uno de los campos del reporte
        #_logger.warning(f'_get_additional_column_aml_values: {res}')
        return res

    
    def _get_order_by_aml_values(self):
        res = super(PartnerLedgerCustomHandler, self)._get_order_by_aml_values()
        #se ejecuta cuando se desplega uno de los campos del reporte
        #_logger.warning(f'_get_order_by_aml_values: {res}')
        return res
    
    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        res = super(PartnerLedgerCustomHandler, self)._get_aml_values(options, partner_ids, offset, limit)
        #se ejecuta cuando se desplega uno de los campos del reporte
        #_logger.warning(f'_get_aml_values: {res}')
        return res

    def _get_report_line_partners(self, options, partner, partner_values, level_shift=0):
        res = super(PartnerLedgerCustomHandler, self)._get_report_line_partners(options, partner, partner_values, level_shift)
        #método se ejecuta al entrar
        #_logger.warning(f'_get_report_line_partners: {res}')
        return res

    def _get_no_partner_line_label(self):
        res = super(PartnerLedgerCustomHandler, self)._get_no_partner_line_label()
        #metodo se ejecuta al entrar
        #_logger.warning(f'_get_no_partner_line_label: {res}')
        return res

    @api.model
    def _format_aml_name(self, line_name, move_ref, move_name=None):
        res = super(PartnerLedgerCustomHandler, self)._format_aml_name(line_name, move_ref, move_name)
        #se ejecuta cuando se desplega uno de los campos del reporte
        #_logger.warning(f'_format_aml_name: {res}')
        return res
    
    def _get_report_line_move_line(self, options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=0):
        res = super(PartnerLedgerCustomHandler, self)._get_report_line_move_line(options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift)
        #se ejecuta cuando se desplega uno de los campos del reporte
        #_logger.warning(f'_get_report_line_move_line: {res}')
        return res
    
    def _get_report_line_total(self, options, totals_by_column_group):
        res = super(PartnerLedgerCustomHandler, self)._get_report_line_total(options, totals_by_column_group)
        #método se ejecuta al entrar
        #_logger.warning(f'_get_report_line_total: {res}')
        return res
    