# -*- coding: utf-8 -*-
################################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
################################################################################
{
    "name": "l10_ar Tax extended",
    "summary": "",
    'version': "18.0.1.0.4",
    'author': 'Mastercore Sinapsys Global®',
    'website': 'https://www.mastercore.us',
    'license': 'OPL-1',
    'category': "accounting",
    "depends": [
        'l10n_ar_tax',
        'account_payment_pro'
    ],
    "data": [
        'views/res_config_settings.xml',
        'views/l10n_ar_payment_withholding.xml'
    ],
}
