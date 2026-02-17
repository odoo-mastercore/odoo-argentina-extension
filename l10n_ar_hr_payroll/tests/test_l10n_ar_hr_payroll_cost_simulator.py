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


class TestL10nArHrPayrollCostSimulator(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref("base.ar")
        cls.structure_type = cls.env.ref("l10n_ar_hr_payroll.l10n_ar_employee")
        cls.wizard_model = cls.env["l10n.ar.hr.payroll.cost.simulator.wizard"]

    def test_new_hire_simulation_includes_sac_and_vacation(self):
        wizard = self.wizard_model.create({
            "mode": "new_hire",
            "company_id": self.env.company.id,
            "structure_type_id": self.structure_type.id,
            "reference_year": 2026,
            "contract_start_date": date(2026, 1, 1),
            "seniority_date": date(2026, 1, 1),
            "proposed_gross_monthly": 1200000.0,
            "proposed_union_rate": 2.0,
            "proposed_seniority_percent": 1.0,
        })
        wizard.action_simulate()
        self.assertTrue(wizard.result_ready)
        self.assertGreater(wizard.proposed_annual_total_cost, 0.0)

        sac_lines = wizard.line_ids.filtered(
            lambda line: line.scenario == "proposed" and line.component == "sac" and line.periodicity == "annual"
        )
        vacation_lines = wizard.line_ids.filtered(
            lambda line: line.scenario == "proposed" and line.component == "vacation" and line.periodicity == "annual"
        )

        self.assertTrue(sac_lines)
        self.assertTrue(vacation_lines)
        self.assertGreater(sac_lines[0].gross_amount, 0.0)
        self.assertGreater(vacation_lines[0].gross_amount, 0.0)

    def test_salary_increase_delta_is_positive(self):
        employee = self.env["hr.employee"].create({
            "name": "Empleado Simulacion",
            "company_id": self.env.company.id,
        })
        version = employee.version_id
        version.write({
            "company_id": self.env.company.id,
            "structure_type_id": self.structure_type.id,
            "wage": 1000000.0,
            "date_start": date(2020, 1, 1),
            "contract_date_start": date(2020, 1, 1),
            "l10n_ar_seniority_date": date(2020, 1, 1),
            "l10n_ar_union_rate": 2.0,
            "l10n_ar_seniority_percent": 1.0,
        })

        wizard = self.wizard_model.create({
            "mode": "salary_increase",
            "company_id": self.env.company.id,
            "employee_id": employee.id,
            "structure_type_id": self.structure_type.id,
            "reference_year": 2026,
            "contract_start_date": date(2020, 1, 1),
            "seniority_date": date(2020, 1, 1),
            "current_gross_monthly": 1000000.0,
            "proposed_gross_monthly": 1250000.0,
            "current_union_rate": 2.0,
            "proposed_union_rate": 2.0,
            "current_seniority_percent": 1.0,
            "proposed_seniority_percent": 1.0,
        })
        wizard.action_simulate()
        self.assertTrue(wizard.result_ready)
        self.assertGreater(wizard.delta_regular_monthly_cost, 0.0)
        self.assertGreater(wizard.delta_prorated_monthly_cost, 0.0)
        self.assertGreater(wizard.delta_annual_total_cost, 0.0)
