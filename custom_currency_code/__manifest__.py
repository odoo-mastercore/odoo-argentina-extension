# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2021-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
{
    'name': "Custom Currency Code",
    'version': "16.0.1",
    'description': '',
    'summary': "",
    'author': "SINAPSYS GLOBAL SA || MASTERCORE SAS",
    'website': "http://sinapsys.global",
    'license': 'AGPL-3',
    'category': 'Accounting',
    'depends': ['base', 'account', 'account_accountant'],
    'installable': True,
    'auto_install': False,
    'data': [
        #'security/ir.model.access.csv',
        'view/views.xml',
    ],
    'application': False,
}
