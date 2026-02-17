# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
# See https://www.gnu.org/licenses/agpl-3.0.html
#
##############################################################################

from datetime import date

from odoo.tests.common import TransactionCase


class TestL10nArHrPayroll(TransactionCase):

    def test_cuil_normalization(self):
        employee = self.env["hr.employee"].create({
            "name": "Empleado AR",
            "l10n_ar_cuil": "20 12345678 6",
        })
        self.assertEqual(employee.l10n_ar_cuil, "20-12345678-6")

    def test_vacation_days_by_seniority(self):
        employee = self.env["hr.employee"].create({
            "name": "Empleado Antiguedad",
            "company_id": self.env.company.id,
        })
        version = employee.version_id
        version.write({
            "structure_type_id": self.env.ref("l10n_ar_hr_payroll.l10n_ar_employee").id,
            "wage": 1000000.0,
            "date_start": date(2018, 1, 1),
            "l10n_ar_seniority_date": date(2018, 1, 1),
            "company_id": self.env.company.id,
        })
        payslip = self.env["hr.payslip"].create({
            "employee_id": employee.id,
            "company_id": self.env.company.id,
            "version_id": version.id,
            "struct_id": self.env.ref("l10n_ar_hr_payroll.l10n_ar_vacation_pay").id,
            "date_from": date(2026, 1, 1),
            "date_to": date(2026, 1, 31),
        })
        self.assertEqual(payslip._l10n_ar_get_vacation_days(), 21)
