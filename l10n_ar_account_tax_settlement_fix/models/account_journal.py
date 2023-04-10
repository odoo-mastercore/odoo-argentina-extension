# -*- coding: utf-8 -*-
##############################################################################
# Author: SINAPSYS GLOBAL SA || MASTERCORE SAS
# Copyleft: 2023-Present.
# License LGPL-3.0 or later (http: //www.gnu.org/licenses/lgpl.html).
#
#
###############################################################################
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round
import re

#########
# helpers
#########

def format_amount(amount, padding=15, decimals=2, sep=""):
    if amount < 0:
        template = "-{:0>%dd}" % (padding - 1 - len(sep))
    else:
        template = "{:0>%dd}" % (padding - len(sep))
    res = template.format(
        int(round(abs(amount) * 10**decimals, decimals)))
    if sep:
        res = "{0}{1}{2}".format(res[:-decimals], sep, res[-decimals:])
    return res

def get_line_tax_base(move_line):
    return sum(move_line.move_id.line_ids.filtered(
        lambda x: move_line.tax_line_id in x.tax_ids).mapped(
        'balance'))

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def iibb_aplicado_files_values(self, move_lines, act_7=None):
        """
        Por ahora es el de arba, renombrar o generalizar para otros
        Implementado segun esta especificacion
        https://drive.google.com/file/d/0B3trzV0e2WzveHhBTk9xWEl6RjA/view
        Implementados:
            - 1.2 Percepciones Act. 7 método Percibido (quincenal)
            - 1.7 Retenciones ( excepto actividad 26, 6 de Bancos y 17 de
            Bancos y No Bancos)
        """
        self.ensure_one()
        ret = ''
        perc = ''

        for line in move_lines:
            # pay_group = payment.payment_group_id
            move = line.move_id
            payment = line.payment_id
            internal_type = line.l10n_latam_document_type_id.internal_type
            document_code = line.l10n_latam_document_type_id.code

            line.partner_id.ensure_vat()

            content = line.partner_id.l10n_ar_formatted_vat
            content += fields.Date.from_string(
                line.date).strftime('%d/%m/%Y')

            # solo para percepciones
            if not payment:
                content += (
                    document_code in ['201', '206', '211'] and 'E' or
                    document_code in ['203', '208', '213'] and 'H' or
                    document_code in ['202', '207', '212'] and 'I' or
                    internal_type == 'invoice' and 'F' or
                    internal_type == 'credit_note' and 'C' or
                    internal_type == 'debit_note' and 'D' or 'R')
                content += line.l10n_latam_document_type_id.l10n_ar_letter
            document_parts = {}
            # Tomamos el número de comprobante dependiendo si es Ret / Perc
            if not payment:
                document_parts = move._l10n_ar_get_document_number_parts(
                    move.l10n_latam_document_number, move.l10n_latam_document_type_id.code)
            else:
                document_parts = move._l10n_ar_get_document_number_parts(
                    line.payment_id.withholding_number, False)
            # si el punto de venta es de 5 digitos no encontramos doc
            # que diga como proceder, tomamos los ultimos 4 digitos
            pto_venta = "{:0>4d}".format(document_parts['point_of_sale'])[-4:]
            nro_documento = "{:0>8d}".format(document_parts['invoice_number'])[-8:]
            content += str(pto_venta)
            content += str(nro_documento)

            # solo para percepciones
            if not payment:
                content += format_amount(-get_line_tax_base(line), 12, 2, ',')

            # este es para el primer tipo de la especificación
            content += format_amount(-line.balance, 11, 2, ',')

            # solo para percepciones
            # según especificación se requiere fecha nuevamente
            # por ahora lo sacamos ya que en ticket 16448 nos mandaron ej.
            # donde no se incluía, en realidad tal vez depende de la actividad
            # ya que en la primer tabla del pdf la agrega y en la segunda no
            if act_7 and not payment:
                content += fields.Date.from_string(
                    line.date).strftime('%d/%m/%Y')
            content += 'A'
            content += '\r\n'

            if payment:
                ret += content
            else:
                perc += content

        # para la fecha de la presentación tomamos la fecha de un apunte a liquidar
        # el valor de la quincena puede ser 0, 1, 2. deberiamos ver si podemos
        # completarlo de alguna manera
        period = move_lines and \
            fields.Date.from_string(move_lines[0].date).strftime('%Y%mX') or ""

        # AR-CUIT-PERIODO-ACTIVIDAD-LOTE_MD5
        perc_txt_filename = "AR-%s-%s-%s-LOTEX.txt" % (
            self.company_id.vat,
            period,
            "7",  # 7 serian las percepciones
        )

        # AR-vat-PERIODO-ACTIVIDAD-LOTE_MD5
        ret_txt_filename = "AR-%s-%s-%s-LOTEX.txt" % (
            self.company_id.vat,
            period,
            "6",  # 6 serian las retenciones
        )

        return [
            {
                'txt_filename': perc_txt_filename,
                'txt_content': perc,
            },
            {
                'txt_filename': ret_txt_filename,
                'txt_content': ret,
            }]
