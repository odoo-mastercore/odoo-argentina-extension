from odoo import fields, models, _, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.date_utils import get_timedelta
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order.template"

    draft_invoices = fields.Boolean('Generar Factura en borrador', default=False)
