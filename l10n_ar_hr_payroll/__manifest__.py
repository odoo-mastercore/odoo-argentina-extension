# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
# See https://www.gnu.org/licenses/agpl-3.0.html
#
##############################################################################

{
    "name": "Argentina - Payroll",
    "countries": ["ar"],
    "category": "Human Resources/Payroll",
    "depends": ["l10n_ar", "hr_payroll", "hr_work_entry_holidays", "hr_payroll_holidays"],
    "auto_install": ["hr_payroll"],
    "version": "1.0.2",
    "description": """
Argentinian Payroll Rules.
==========================

    * Employee and contract payroll fields for Argentina
    * Salary structures for regular payroll, SAC and vacations
    * Salary rules for employee deductions and employer contributions
    * Rule parameters for legal percentages and divisors
    """,
    "data": [
        "data/hr_salary_rule_category_data.xml",
        "views/hr_payroll_report.xml",
        "views/report_payslip_templates.xml",
        "views/hr_payslip_views.xml",
        "data/hr_payroll_structure_type_data.xml",
        "data/hr_payroll_structure_data.xml",
        "data/hr_payroll_structure_report_data.xml",
        "data/hr_rule_parameters_data.xml",
        "data/hr_payslip_input_type_data.xml",
        "data/salary_rules/hr_salary_rule_regular_pay_data.xml",
        "data/salary_rules/hr_salary_rule_sac_data.xml",
        "data/salary_rules/hr_salary_rule_vacation_data.xml",
        "views/hr_employee_views.xml",
        "views/hr_contract_template_views.xml",
    ],
    "author": "Mastercore",
    "license": "AGPL-3",
}
