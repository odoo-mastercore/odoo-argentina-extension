# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2022-Present.
#
#
###############################################################################
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.onchange('payment_group_id')
    def onchange_payment_group_id(self):
        # now we change this according when use save & new the context from the payment was erased and we need to use some data.
        # this change is due this odoo change https://github.com/odoo/odoo/commit/c14b17c4855fd296fd804a45eab02b6d3566bb7a
        if self.payment_group_id:
            self.date = self.payment_group_id.payment_date
            self.partner_type = self.payment_group_id.partner_type
            self.partner_id = self.payment_group_id.partner_id
            self.payment_type = 'inbound' if self.payment_group_id.partner_type  == 'customer' else 'outbound'
            self.amount = self.payment_group_id.payment_difference
            if self.payment_group_id.apply_foreign_payment:
                self.currency_id = self.payment_group_id.selected_debt_currency_id.id
                self.amount = self.payment_group_id.selected_financial_debt_currency
                self.amount_company_currency = self.payment_group_id.selected_financial_debt_currency * self.payment_group_id.exchange_rate_applied
                self.exchange_rate = self.payment_group_id.exchange_rate_applied

    @api.depends('amount', 'other_currency', 'amount_company_currency')
    def _compute_exchange_rate(self):
        for rec in self:
            if rec.other_currency:
                if not rec.payment_group_id.apply_foreign_payment:
                    rec.exchange_rate = rec.amount and (
                        rec.amount_company_currency / rec.amount) or 0.0
                else:
                    rec.exchange_rate = rec.payment_group_id.exchange_rate_applied
                    rec.amount = rec.amount_company_currency / rec.exchange_rate
            else:
                rec.exchange_rate = False

    # this onchange is necesary because odoo, sometimes, re-compute
    # and overwrites amount_company_currency. That happends due to an issue
    # with rounding of amount field (amount field is not change but due to
    # rouding odoo believes amount has changed)
    @api.onchange('amount_company_currency')
    def _inverse_amount_company_currency(self):

        for rec in self:
            if not rec.payment_group_id.apply_foreign_payment:
                if rec.other_currency and rec.amount_company_currency != \
                        rec.currency_id._convert(
                            rec.amount, rec.company_id.currency_id,
                            rec.company_id, rec.date):
                    force_amount_company_currency = rec.amount_company_currency
                else:
                    force_amount_company_currency = False
                rec.force_amount_company_currency = force_amount_company_currency
            else:
                rec.force_amount_company_currency = rec.amount_company_currency

    @api.depends('amount', 'other_currency', 'force_amount_company_currency')
    def _compute_amount_company_currency(self):
        """
        * Si las monedas son iguales devuelve 1
        * si no, si hay force_amount_company_currency, devuelve ese valor
        * sino, devuelve el amount convertido a la moneda de la cia
        """
        for rec in self:
            if not rec.payment_group_id.apply_foreign_payment:
                if not rec.other_currency:
                    amount_company_currency = rec.amount
                elif rec.force_amount_company_currency:
                    amount_company_currency = rec.force_amount_company_currency
                else:
                    amount_company_currency = rec.currency_id._convert(
                        rec.amount, rec.company_id.currency_id,
                        rec.company_id, rec.date)
                rec.amount_company_currency = amount_company_currency
            else:
                rec.amount_company_currency = rec.force_amount_company_currency
                if rec.tax_withholding_id:
                    withholding_amount = rec.computed_withholding_amount
                    exchange_rate = rec.payment_group_id.exchange_rate_applied or 1
                    amount = withholding_amount / exchange_rate
                    rec.write({
                        'amount_company_currency': withholding_amount,
                        'exchange_rate': exchange_rate,
                        'amount': amount,
                        'withholding_base_amount': rec.withholdable_base_amount / exchange_rate
                    })


    def _get_blocking_l10n_latam_warning_msg(self):
        msgs = []
        for rec in self.filtered('l10n_latam_check_id'):
            if not rec.payment_group_id.apply_foreign_payment:
                if not rec.currency_id.is_zero(rec.l10n_latam_check_id.amount - rec.amount):
                    msgs.append(_(
                        'The amount of the payment (%s) does not match the amount of the selected check (%s). '
                        'Please try to deselect and select the check again.', rec.amount, rec.l10n_latam_check_id.amount))
            if rec.payment_method_line_id.code in ['in_third_party_checks', 'out_third_party_checks']:
                if rec.l10n_latam_check_id.state != 'posted':
                    msgs.append(_('Selected check "%s" is not posted', rec.l10n_latam_check_id.display_name))
                elif (rec.payment_type == 'outbound' and
                        rec.l10n_latam_check_id.l10n_latam_check_current_journal_id != rec.journal_id) or (
                        rec.payment_type == 'inbound' and rec.is_internal_transfer and
                        rec.l10n_latam_check_id.l10n_latam_check_current_journal_id != rec.destination_journal_id):
                    # check outbound payment and transfer or inbound transfer
                    msgs.append(_(
                        'Check "%s" is not anymore in journal "%s", it seems it has been moved by another payment.',
                        rec.l10n_latam_check_id.display_name, rec.journal_id.name
                        if rec.payment_type == 'outbound' else rec.destination_journal_id.name))
                elif rec.payment_type == 'inbound' and not rec.is_internal_transfer and \
                        rec.l10n_latam_check_id.l10n_latam_check_current_journal_id:
                    msgs.append(_("Check '%s' is on journal '%s', it can't be received it again",
                                rec.l10n_latam_check_id.display_name, rec.journal_id.name))
        return msgs

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for pay in self:
            if pay.payment_group_id:
                if pay.payment_group_id.apply_foreign_payment:
                    pay.currency_id = pay.payment_group_id.selected_debt_currency_id
            else:
                pay.currency_id = pay.journal_id.currency_id or pay.journal_id.company_id.currency_id