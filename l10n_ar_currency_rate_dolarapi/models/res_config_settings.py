# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
#
###############################################################################

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dolarapi_data_source = fields.Selection(
        selection=[
            ('oficial', 'BNA official (dolar oficial)'),
            ('bolsa', 'MEP (bolsa)'),
        ],
        string="Argentina dolarapi.com source",
        config_parameter='dolarapi.com.data.source',
        default='oficial',
    )