# -*- coding: utf-8 -*-
################################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
################################################################################
{
    'name': "Reports Filter Account",
    'version': "18.0.0.0",
    'description': '',
    'summary': "",
    'author': 'Mastercore Sinapsys Global®',
    'website': 'https://www.mastercore.us',
    'license': 'OPL-1',
    'category': 'Accounting',
    'depends': [
        'account_followup',
        'account_reports',
    ],
    'data': [
        'view/account_report_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_reports_filter_account/static/src/js/exclude_zero_balance_filter.js',
            'l10n_reports_filter_account/static/src/xml/account_report_filters.xml',
        ],
    },

    #'assets': {
     #   'web.assets_backend': ['l10n_reports_filter_account/static/src/js/account_reports.js'],
     #   },
    #'data': [
    #    'view/general_ledger.xml',
    #],
    'application': True,
    'installable': True,
    'auto_install': False,
}