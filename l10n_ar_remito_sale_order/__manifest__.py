# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
{
    "name": "l10n ar remito sale order",
    "summary": "",
    'version': "16.0.0.0.8",
    'author': 'SINAPSYS GLOBAL SA || MASTERCORE SAS',
    'website': "http://sinapsys.global",
    'category': "sale",
    "license": "AGPL-3",
    "depends": [
        "sale_management",
        "l10n_ar_stock"
    ],
    "data": [
        'data/ir_sequence_data.xml',
        'data/stock_book.xml',
        'views/sale_order.xml',
        'views/remito_report.xml',
        'views/res_partner.xml'
    ],
}
