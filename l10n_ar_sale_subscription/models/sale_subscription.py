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
from dateutil.relativedelta import relativedelta
import logging
import requests
import json

_logger = logging.getLogger(__name__)

class SaleSubscriptionInherit(models.Model):
    _inherit = 'sale.subscription'

    def _prepare_invoice_data(self):
        res = super(SaleSubscriptionInherit, self)._prepare_invoice_data()
        next_date = self.recurring_next_date
        recurring_next_date = self._get_recurring_next_date(self.recurring_rule_type, \
            self.recurring_interval, next_date, self.recurring_invoice_day)
        end_date = fields.Date.from_string(recurring_next_date) - relativedelta(days=1)
        if self.template_id.recurring_invoicing_type == 'pre_paid' and \
            self.recurring_rule_type == 'monthly' and self.recurring_interval == 1:
            res.update({
                "l10n_ar_afip_service_start": format_date(self.env, next_date),
                "l10n_ar_afip_service_end": format_date(self.env, end_date),
            })
        elif self.template_id.recurring_invoicing_type == 'post_paid' and \
            self.recurring_rule_type == 'monthly' and self.recurring_interval == 1:
            next_date = self.recurring_next_date - relativedelta(months = 1)
            recurring_next_date = self._get_recurring_next_date(self.recurring_rule_type, \
            self.recurring_interval, next_date, self.recurring_invoice_day)
            end_date = fields.Date.from_string(recurring_next_date) - relativedelta(days=1)
            res.update({
                "narration": _("This invoice covers the following period: %s - %s") % (format_date(self.env, next_date), format_date(self.env, end_date)),
                "l10n_ar_afip_service_start": next_date,
                "l10n_ar_afip_service_end": end_date,
            })
        return res