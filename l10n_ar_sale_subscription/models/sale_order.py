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
from dateutil.relativedelta import relativedelta
from odoo.tools import format_date
from datetime import datetime, timedelta
from odoo.tools.date_utils import get_timedelta
import logging
import requests
import json

_logger = logging.getLogger(__name__)

class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        if self.sale_order_template_id.recurring_invoicing_type == 'post_paid':
            start_date_service = self.next_invoice_date and \
                self.next_invoice_date - get_timedelta(self.recurrence_id.duration, \
                    self.recurrence_id.unit)
            end_date_service = self.next_invoice_date - relativedelta(days=1)
          
            vals['l10n_ar_afip_service_start'] = start_date_service
            vals['l10n_ar_afip_service_end'] = end_date_service
        elif self.sale_order_template_id.recurring_invoicing_type == 'pre_paid':
            end_date_service = self.next_invoice_date and \
                self.next_invoice_date + get_timedelta(self.recurrence_id.duration, \
                    self.recurrence_id.unit)
            start_date_service = self.next_invoice_date
          
            vals['l10n_ar_afip_service_start'] = start_date_service
            vals['l10n_ar_afip_service_end'] = end_date_service
        return vals
