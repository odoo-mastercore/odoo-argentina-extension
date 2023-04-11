# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
{
    "name": "Payment Group in Foreign currency",
    "summary": "",
    'version': "16.0.2.2",
    'author': 'SINAPSYS GLOBAL SA || MASTERCORE SAS',
    'website': "http://sinapsys.global",
    'category': "contact",
    "license": "AGPL-3",
    "depends": [
        'account_payment_group',
        'l10n_ar_ux',
        'l10n_ar_account_withholding'
    ],
    "data": [
        "views/account_payment_group_view.xml",
        "reports/report_withholding_certificate.xml"
    ],
}
