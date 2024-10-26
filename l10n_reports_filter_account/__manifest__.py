##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2021-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
{
    'name': "Reports Filter Account",
    'version': "15.0.0.1",
    'description': '',
    'summary': "",
    'author': "SINAPSYS GLOBAL SA || MASTERCORE SAS",
    'website': "http://sinapsys.global",
    'license': 'AGPL-3',
    'category': 'Accounting',
    'depends': [
        'account_followup',
        'account_reports',
    ],
    'assets': {
        'web.assets_backend': ['l10n_reports_filter_account/static/src/js/account_reports.js'],
        },
    'data': [
        'view/general_ledger.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}