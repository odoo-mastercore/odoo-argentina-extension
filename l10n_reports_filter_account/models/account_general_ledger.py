# -*- coding: utf-8 -*-
################################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
################################################################################

from odoo import models


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = "account.general.ledger.report.handler"

    def _query_values(self, report, options):
        accounts_results = super()._query_values(report, options)
        if not options.get('exclude_zero_balance'):
            return accounts_results
        
        filtered_results = []

        for account, results in accounts_results:
            balances = []

            for column_group_key in options['column_groups']:
                column_group_results = results.get(column_group_key, {})
                account_sum = column_group_results.get('sum', {})
                unaffected_earnings = column_group_results.get('unaffected_earnings',{},)
                balance = ( account_sum.get('balance', 0.0)+ unaffected_earnings.get('balance', 0.0))
                balances.append(balance)

            if any(balance != 0.0 for balance in balances):
                filtered_results.append((account, results))

        return filtered_results