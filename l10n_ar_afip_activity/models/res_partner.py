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
    
    def create(self,vals):
        rec = super(ResPartner, self).create(vals)
        _logges.warning(self.actividades_padron[0])
        if self.actividades_padron:
            self.industry_id = self.actividades_padron[0]
        return rec

    def write(self,vals):
        rec = super(ResPartner, self).write(vals)
        _logges.warning(self.actividades_padron[0])
        if self.actividades_padron:
            self.industry_id = self.actividades_padron[0]
        return rec
    
        
