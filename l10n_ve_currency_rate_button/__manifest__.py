# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
{
    'name': "Tasa Monedas en NAVBAR (Backend)",
    'description': """
        Muestra una etiqueta con las tasas activas en odoo y su conversión en la
        barra superior de odoo
    """,
    'author': 'SINAPSYS GLOBAL SA || MASTERCORE SAS',
    'website': 'www.sinapsys.global',
    "version": "16.0.1.0.1",
    'license': 'AGPL-3',
    'category': 'account',
    'depends': [],
    'assets': {
        'web.assets_backend': [
            'l10n_ve_currency_rate_button/static/src/js/currency_rates.js',
            'l10n_ve_currency_rate_button/static/src/xml/currency_rate.xml',
            'l10n_ve_currency_rate_button/static/src/css/main.css'
        ],
    },
    'data': [
        'views/res_currency.xml'
    ],
    'installable': True,
}