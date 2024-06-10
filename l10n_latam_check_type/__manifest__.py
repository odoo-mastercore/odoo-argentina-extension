# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0) 
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
###############################################################################
{
    "name": "Mastercore L10N Custom - L10n Latam Check type",
    'summary': """
        The l10n_latam_check_type module enhances the Odoo localization 
        for Argentina by introducing support for different check types 
        specific to the region. It allows businesses to manage and process 
        various types of checks, ensuring compliance with local financial regulations. 
    """
    'version': "16.0.1.1",
    'author': "Mastercore Sinapsys Global®",
    'website': "https://www.mastercore.us",
    'sequence': 1,
    'category': "sale",
    "license": "AGPL-3",
    "depends": [
        "l10n_latam_check"
    ],
    "data": [
        'views/account_payment_view.xml'
    ],
    'installable': True,
    'auto_install': False
}
