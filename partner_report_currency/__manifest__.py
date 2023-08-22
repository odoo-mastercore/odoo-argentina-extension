# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2021-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
{
    'name': "Partner Report by Currency",
    'version': "16.0.1",
    'description': '',
    'summary': "",
    'author': "SINAPSYS GLOBAL SA || MASTERCORE SAS",
    'website': "http://sinapsys.global",
    'license': 'AGPL-3',
    'category': 'Accounting',
    'depends': ['base', 'account', 'account_accountant', 'account_reports'],
    'installable': True,
    'auto_install': False,
    'assets': {
        #'web.assets_backend': ['gl_foreign_currency/static/src/js/account_reports.js'],
        },
    'data': [
        'security/ir.model.access.csv',
        'view/views_actions.xml',
        'view/partner_pending_payments.xml',
        'view/partner_account_status.xml',
        'wizard/partner_account_status_report.xml',
    ],
    'application': False,
}
