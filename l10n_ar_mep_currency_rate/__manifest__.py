# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3 
#
###############################################################################
{
     'name': 'Argentina - dolarapi.com MEP/BNA Currency Rate',
     'version': '17.0.1.2',
     'category': 'Accounting/Accounting',
     'sequence': 1,
     'summary': 'Actualización de Tasa Dolar MEP (bolsa) o BNA (oficial) Argentina',
     'description': """
This module provides automatic updates for the MEP (Mercado Electrónico de Pagos) or BNA exchange rate in Argentina using the dolarapi.com service. It is specifically designed for businesses and financial institutions that require daily and accurate information on the MEP or BNA dollar to manage their accounting and operations efficiently. The module includes a scheduled task that fetches the latest MEP or BNA exchange rate and integrates it seamlessly into Odoo’s currency rates, ensuring that all financial transactions are up to date with the latest market data.
""",
     'author': 'Mastercore Sinapsys Global®',
     'website': 'https://www.mastercore.us',
     'license': 'AGPL-3',
     'depends': ['base'],
     'data':[
        'data/ir_cron_data.xml',
        'data/if_config_parameter_data.xml'
     ],
     'installable': True,
     'application': False,
}