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


class accountPaymentGroup(models.Model):
    _inherit = 'account.payment.group'

    def post(self):
        for rec in self:
            check_in_id = self.env.ref('l10n_latam_check.account_payment_method_in_third_party_checks').id
            check_out_id = self.env.ref('l10n_latam_check.account_payment_method_out_third_party_checks').id
            new_check = self.env.ref('l10n_latam_check.account_payment_method_new_third_party_checks').id
            checks = rec.payment_ids.filtered(lambda x: x.payment_method_line_id.id in [check_in_id,check_out_id, new_check])
            for element in checks:
                if len(checks.filtered(lambda x: x.number_check_aux == element.number_check_aux and x.l10n_latam_check_bank_id_aux == element.l10n_latam_check_bank_id_aux)) > 1:
                    raise UserError(_('No puede ingresar el mismo cheque mas de una vez'))
        return super(accountPaymentGroup,self).post()