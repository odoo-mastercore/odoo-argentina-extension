# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2022-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
{
    'name': "Facturas Pendientes",
    'description': """
        **Presupuesto**
        Modulo que agrega un boton en el presupuesto para visualizar las facturas pendientes del clientes
    """,

    'author': "SINAPSYS GLOBAL SA || MASTERCORE SAS",
    'website': "http://sinapsys.global",
    'version': '16.0.2',
    'category': 'Sale',
    'license': 'LGPL-3',
    'depends': ['sale', 'account','base'],
    'data': [
        'views/sale_order_views.xml',
        'views/pending_invoices.xml'
    ],
    
}
