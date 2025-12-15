# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
# See https://www.gnu.org/licenses/agpl-3.0.html
#
###############################################################################
{
    'name': 'Argentina - Currency Rate Provider (dolarapi BNA/MEP)',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'sequence': 1,
    'summary': 'Argentina: exchange rate provider using dolarapi.com (BNA official or MEP/bolsa).',
    'description': """
This module adds an Argentina-specific exchange rate provider based on dolarapi.com,
integrated with Odoo Enterprise 'currency_rate_live' framework.

It allows selecting the source (BNA official or MEP/bolsa) through Settings and
updates the USD rate for AR companies using the standard Odoo currency rate scheduler.
""",
    'author': 'Mastercore Sinapsys Global®',
    'website': 'https://www.mastercore.us',
    'license': 'AGPL-3',
    'depends': [
        'currency_rate_live',
    ],
    'data': [
        'data/ir_config_parameter_data.xml',
        'views/res_config_settings_view.xml',
    ],
    'installable': True,
    'application': False,
}