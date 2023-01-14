# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2022-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
from odoo import api, fields, models, tools
import logging

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):

    _inherit = "res.partner"
    
    @api.model
    def create(self, vals):
        res = super(ResPartner, self).create(vals)
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
        
        return res

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
        
    
        
