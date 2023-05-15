# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2021-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
{
    'name': 'Foreign Currency',
    'version': '16.0.0.1.25',
    'description': '',
    'summary': '',
    'author': "SINAPSYS GLOBAL SA || MASTERCORE SAS",
    'website': "http://sinapsys.global",
    'license': 'AGPL-3',
    'category': 'Localization',
    'depends': [
        'account',
        'base',
        'l10n_ar',
    ],
    'data': [
        'views/account_move_view.xml',
        'views/res_company_view.xml'
    ],
    'auto_install': False,
    'application': False,
}
