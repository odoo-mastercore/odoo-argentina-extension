# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2021-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
{
    'name': "General Ledger in Foreign Currency",
    'version': "16.0.1",
    'description': '',
    'summary': "",
    'author': "SINAPSYS GLOBAL SA || MASTERCORE SAS",
    'website': "http://sinapsys.global",
    'license': 'AGPL-3',
    'category': 'Accounting',
    'depends': ['base','account','account_reports', 'l10n_latam_foreing_currency', 'l10n_ar_ux'],
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': ['gl_foreign_currency/static/src/js/account_reports.js'],
        },
    'data': [
        'view/general_ledger.xml',
    ],
    'application': False,
    'post_init_hook': 'post_init_hook',
}
