# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
{
    "name": "l10n latam check details",
    "summary": "",
    'version': "16.0.0.0.2",
    'author': 'SINAPSYS GLOBAL SA || MASTERCORE SAS',
    'website': "http://sinapsys.global",
    'category': "sale",
    "license": "AGPL-3",
    "depends": [
        "account_payment_group",
        "l10n_latam_check"
    ],
    "data": [
       'views/account_payment.xml',
       'views/account_payment_add_checks_views.xml'
    ],
}
