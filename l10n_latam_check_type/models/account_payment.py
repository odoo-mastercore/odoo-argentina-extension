# -*- coding: utf-8 -*-
###############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################

from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError, UserError


class accountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_latam_check_type = fields.Selection([
        ('E-Check', 'E-Check'),
        ('Físico', 'Físico'),
    ], string='Tipo de cheque')