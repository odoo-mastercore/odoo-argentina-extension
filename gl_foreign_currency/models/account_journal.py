# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields
from datetime import datetime, timedelta
from odoo.tools.misc import format_date

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter
import io

class AccountJournal(models.AbstractModel):
    _inherit = "account.journal"
    
    exclude_report = fields.Boolean(string='Excluir del reporte LME', default=False)