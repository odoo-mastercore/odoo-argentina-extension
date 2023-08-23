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

    number_check_aux = fields.Char('Número de cheque')
    l10n_latam_check_bank_id_aux = fields.Many2one(
        comodel_name='res.bank',
        string='Banco del cheque',
    )

    @api.onchange('l10n_latam_check_number')
    def _onchange_l10n_latam_check_number(self):
        if self.l10n_latam_check_number:
            self.number_check_aux =  self.l10n_latam_check_number

    @api.onchange('l10n_latam_check_bank_id')
    def _onchange_l10n_latam_check_bank_id(self):
        if self.l10n_latam_check_bank_id:
            self.l10n_latam_check_bank_id_aux =  self.l10n_latam_check_bank_id.id

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for index, rec in enumerate(records):
            if vals_list[index].get('l10n_latam_check_number', False):
                rec.number_check_aux = vals_list[index].get('l10n_latam_check_number')
            if vals_list[index].get('l10n_latam_check_bank_id', False):
                rec.l10n_latam_check_bank_id_aux = vals_list[index].get('l10n_latam_check_bank_id')
            if vals_list[index].get('check_number', False) == False and vals_list[index].get('l10n_latam_check_number', False):
                rec.check_number = vals_list[index].get('l10n_latam_check_number')
            if vals_list[index].get('l10n_latam_check_bank_id', False) == False and vals_list[index].get('l10n_latam_check_bank_id_aux', False):
                rec.l10n_latam_check_bank_id = vals_list[index].get('l10n_latam_check_bank_id_aux')
        return records
    
    def write(self, vals):
        if vals.get('l10n_latam_check_number', False):
            vals.update({
                'number_check_aux': vals.get('l10n_latam_check_number', False)
            })
        if vals.get('l10n_latam_check_bank_id', False):
            vals.update({
                'l10n_latam_check_bank_id_aux': vals.get('l10n_latam_check_bank_id', False)
            })
        if not vals.get('l10n_latam_check_bank_id', False) and self.l10n_latam_check_bank_id_aux:
            vals.update({
                'l10n_latam_check_bank_id': self.l10n_latam_check_bank_id_aux            
            })
        return super(accountPayment, self).write(vals)