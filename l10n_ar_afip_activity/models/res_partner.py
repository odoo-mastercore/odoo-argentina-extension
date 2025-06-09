# -*- coding: utf-8 -*-
################################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License OPL-1 (Odoo Proprietary License v1.0)
# See https://www.odoo.com/documentation/master/legal/licenses.html
#
################################################################################
from odoo import api, models

class ResPartner(models.Model):
    _inherit = "res.partner"
    
    @api.model_create_multi
    def create(self, vals_list):
        vals = super(ResPartner, self).create(vals_list)
        for res in vals:
            if res.actividades_padron:
                activity_name = res.actividades_padron[0].name
                exist =  self.env['res.partner.industry'].search([('name', '=', activity_name)],limit=1)
                if not exist:
                    industry =  self.env['res.partner.industry'].create({
                        'name' : activity_name,
                        'full_name' : activity_name,
                        'active' : True,
                    })
                    res.industry_id = industry
                else:
                    res.industry_id = exist
        return vals

    def write(self, vals):
        res = super(ResPartner, self).write(vals)
        if 'actividades_padron' in vals:
            exist =  self.env['res.partner.industry'].search([('name', '=', self.actividades_padron[0].name)],limit=1)
            if not exist:
                industry =  self.env['res.partner.industry'].create({
                    'name' : self.actividades_padron[0].name,
                    'full_name' : self.actividades_padron[0].name,
                    'active' : True,
                })
                self.industry_id = industry
            else:
                self.industry_id = exist
        return res
