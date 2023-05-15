
from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccounTpaymentAddChecks(models.TransientModel):
    _inherit = "account.payment.add.checks"

    def confirm(self):
        self.ensure_one()
        payment_group = self.env["account.payment.group"].browse(self.env.context.get("active_id", False))
        if payment_group:
            if payment_group.apply_foreign_payment:
                if not payment_group.exchange_rate_applied:
                    raise ValidationError(_("¡Lo sentimos!, Debe configurar"
                    + " el marcador de tipo de cambio con un valor distinto"
                    + " a cero, antes de agregar una linea"))
                vals_list = [{
                    'l10n_latam_check_bank_id': check.l10n_latam_check_bank_id,
                    'l10n_latam_check_number': check.l10n_latam_check_number,
                    'l10n_latam_check_payment_date': check.l10n_latam_check_payment_date,
                    'l10n_latam_check_type': check.l10n_latam_check_type,
                    'l10n_latam_check_id': check.id,
                    'l10n_latam_check_id': check.id,
                    'exchange_rate': payment_group.exchange_rate_applied,
                    'amount': (check.amount_company_currency / payment_group.exchange_rate_applied),
                    'amount_company_currency': check.amount_company_currency,
                    'currency_id': payment_group.selected_debt_currency_id.id,
                    'partner_id': payment_group.partner_id.id,
                    'payment_group_id': payment_group.id,
                    'payment_type': 'outbound',
                    'journal_id': check.l10n_latam_check_current_journal_id.id,
                    'payment_method_line_id': check.l10n_latam_check_current_journal_id._get_available_payment_method_lines(
                        'oubound').filtered(lambda x: x.code == 'out_third_party_checks').id,
                } for check in self.check_ids]
                self.env['account.payment'].create(vals_list)
            else:
                vals_list = [{
                    'l10n_latam_check_bank_id': check.l10n_latam_check_bank_id,
                    'l10n_latam_check_number': check.l10n_latam_check_number,
                    'l10n_latam_check_payment_date': check.l10n_latam_check_payment_date,
                    'l10n_latam_check_type': check.l10n_latam_check_type,
                    'l10n_latam_check_id': check.id,
                    'amount': check.amount if check.currency_id.id \
                        == payment_group.company_id.currency_id.id else \
                        check.amount_company_currency,
                    'partner_id': payment_group.partner_id.id,
                    'payment_group_id': payment_group.id,
                    'payment_type': 'outbound',
                    'journal_id': check.l10n_latam_check_current_journal_id.id,
                    'currency_id': payment_group.company_id.currency_id.id,
                    'payment_method_line_id': check.l10n_latam_check_current_journal_id._get_available_payment_method_lines(
                        'oubound').filtered(lambda x: x.code == 'out_third_party_checks').id,
                } for check in self.check_ids]
                self.env['account.payment'].create(vals_list)
        return {"type": "ir.actions.act_window_close"}
