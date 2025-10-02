# -*- coding: utf-8 -*-
################################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
################################################################################
{
    'name': " Outstanding Credits and Debits UX",
    'version': "0.1",
    'description': '',
    'summary': "",
    'author': 'Mastercore Sinapsys Global®',
    'website': 'https://www.mastercore.us',
    'license': 'OPL-1',
    'category': 'Accounting',
    'depends': [
        'account'
    ],
    'assets': {
        'web.assets_backend': [
            'outstanding_credits_debits_ux/static/src/scss/style.scss',
        ]
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}