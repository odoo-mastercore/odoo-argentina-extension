# -*- coding: utf-8 -*-
{
    'name': "SW - General Ledger in Foreign Currency",
    'summary': "Generate your General Balance report with your preferred currencies",
    'author': "Smart Way Business Solutions",
    'website': "https://www.smartway.co",
    'category': 'Accounting',
    'license':  "Other proprietary",
    'version': "16.0.1",
    'depends': ['base','account','account_reports', 'l10n_latam_foreing_currency'],
    'installable': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': ['gl_foreign_currency/static/src/js/account_reports.js'],
        },
    'data': [
        'view/general_ledger.xml',
    ],
    'images':  ["static/description/image.png"],
    'price' : 50,
    'currency' :  'EUR',
    'post_init_hook': 'post_init_hook',
}
