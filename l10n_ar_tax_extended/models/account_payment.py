# -*- coding: utf-8 -*-
################################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
################################################################################
from odoo import api, models, fields, _, Command
import logging
_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.constrains("currency_id", "company_id", "l10n_ar_withholding_line_ids")
    def _check_withholdings_and_currency(self):
        for rec in self:
            if not rec.company_id.enabled_retention_currency:
                return super()._check_withholdings_and_currency()
            pass

    def _prepare_witholding_write_off_vals(self):
        res = super()._prepare_witholding_write_off_vals()
        for line in self.l10n_ar_withholding_line_ids:
            if line.amount_currency and line.foreign_currency_id and res:
                for i in range(len(res)):
                    if res[i]['name'] == line.name:
                        res[i].update({
                            'currency_id': line.foreign_currency_id.id,
                            'amount_currency': line.amount_currency
                        })
        return res

    @api.depends("l10n_ar_fiscal_position_id", "partner_id", "company_id", "date")
    def _compute_l10n_ar_withholding_line_ids(self):
        """
            Este metodo unifica la logica entre l10n_ar_withholding y l10n_ar_tax_extended
            manteniendo prioridad a la configuracion de la posicion fiscal.
        """
        for rec in self.filtered(lambda x: x.partner_type == "supplier"):
            date = rec.date or fields.Date.context_today(self)
            withholdings = [Command.clear()]
            if rec.l10n_ar_fiscal_position_id.l10n_ar_tax_ids:
                taxes = rec.l10n_ar_fiscal_position_id._l10n_ar_add_taxes(
                    rec.partner_id, rec.company_id, date, "withholding"
                )
                withholdings += [Command.create({"tax_id": x.id}) for x in taxes]
            else:
                partner_taxes = self.env['l10n_ar.partner.tax'].search([
                    *self.env['l10n_ar.partner.tax']._check_company_domain(rec.company_id),
                    '|', ('from_date', '>=', date), ('from_date', '=', False),
                    '|', ('to_date', '<=', date), ('to_date', '=', False),
                    ('partner_id', '=', rec.partner_id.commercial_partner_id.id),
                    ('tax_id.l10n_ar_withholding_payment_type', '=', rec.partner_type)
                ])
                withholdings = [Command.clear()] + [Command.create({'tax_id': x.tax_id.id}) for x in partner_taxes]
            rec.l10n_ar_withholding_line_ids = withholdings