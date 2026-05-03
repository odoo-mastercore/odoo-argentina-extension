# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
# See https://www.gnu.org/licenses/agpl-3.0.html
#
###############################################################################
{
    'name': 'Argentina - Proveedor de Cotización DolarAPI *',
    'version': '19.0.1.2.0',
    'category': 'Accounting/Accounting',
    'sequence': 1,
    'summary': 'Argentina: proveedor de cotización usando dolarapi.com (oficial, mayorista o MEP).',
    'description': """
Este módulo agrega un proveedor de cotización específico para Argentina basado en
dolarapi.com, integrado con el framework Odoo Enterprise 'currency_rate_live'.

Permite seleccionar la fuente (oficial, mayorista o MEP/bolsa) desde Ajustes y
actualiza la cotización de USD para compañías argentinas usando el planificador
estándar de tipos de cambio de Odoo.
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
