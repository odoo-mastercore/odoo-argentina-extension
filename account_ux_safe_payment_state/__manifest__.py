# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
#
##############################################################################
{
    "name": "Estado seguro de pagos Account UX *",
    "summary": "Evita publicar pagos durante el cálculo de su estado",
    "description": """
        Conserva la actualización automática del estado de los pagos de
        Account UX sin ejecutar acciones contables dentro de un campo calculado.
    """,
    "version": "18.0.1.0.0",
    "author": "Mastercore Sinapsys Global®",
    "website": "https://www.mastercore.us",
    "license": "OPL-1",
    "category": "Accounting",
    "depends": [
        "account_ux",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
