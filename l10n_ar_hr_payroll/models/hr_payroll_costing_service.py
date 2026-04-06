# -*- coding: utf-8 -*-
##############################################################################
# Author: Mastercore Sinapsys Global®
# Copyright: 2019-Present.
# License AGPL-3
# See https://www.gnu.org/licenses/agpl-3.0.html
#
##############################################################################

from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class L10nArHrPayrollCostingService(models.AbstractModel):
    _name = "l10n.ar.hr.payroll.costing.service"
    _description = "AR Payroll Costing Service"

    def _l10n_ar_get_simulation_context(self):
        clean_context = {
            key: value
            for key, value in self.env.context.items()
            if not key.startswith("default_")
        }
        clean_context.pop("active_id", None)
        clean_context.pop("active_ids", None)
        clean_context.pop("active_model", None)
        clean_context.update({
            "tracking_disable": True,
            "mail_create_nosubscribe": True,
            "mail_notrack": True,
            "from_planning": False,
        })
        return clean_context

    def _l10n_ar_amount_fields(self):
        return (
            "gross_amount",
            "employee_deductions",
            "net_amount",
            "employer_contributions",
            "employer_total_cost",
        )

    def _l10n_ar_get_payslip_line_total(self, payslip, code):
        line = payslip.line_ids.filtered(lambda payslip_line: payslip_line.code == code)[:1]
        return line.total if line else 0.0

    def _l10n_ar_get_rule_parameter(self, payslip, code):
        value = payslip._rule_parameter(code) or 0.0
        return float(value)

    def _l10n_ar_extract_component_amounts(self, payslip, employer_rate=0.0, employer_from_lines=False):
        currency = payslip.currency_id
        gross_amount = self._l10n_ar_get_payslip_line_total(payslip, "GROSS")
        net_amount = self._l10n_ar_get_payslip_line_total(payslip, "NET")
        employee_deductions = abs(sum(
            payslip.line_ids.filtered(lambda line: line.total < 0 and line.code != "NET").mapped("total")
        ))

        if employer_from_lines:
            employer_contributions = sum(
                payslip.line_ids.filtered(lambda line: line.code in ("AR_CONT_SOC", "AR_ART")).mapped("total")
            )
        else:
            employer_contributions = gross_amount * employer_rate

        return {
            "gross_amount": currency.round(gross_amount),
            "employee_deductions": currency.round(employee_deductions),
            "net_amount": currency.round(net_amount),
            "employer_contributions": currency.round(employer_contributions),
            "employer_total_cost": currency.round(gross_amount + employer_contributions),
        }

    def _l10n_ar_convert_vacation_to_incremental_amounts(
        self,
        wage,
        vacation_days,
        vacation_divisor,
        employee_rate,
        employer_rate,
        currency,
    ):
        vacation_gross = (wage / vacation_divisor) * vacation_days if vacation_divisor else 0.0
        covered_by_regular_gross = (wage / 30.0) * vacation_days
        incremental_gross = max(vacation_gross - covered_by_regular_gross, 0.0)
        incremental_employee_deductions = incremental_gross * employee_rate
        incremental_employer_contributions = incremental_gross * employer_rate
        incremental_net = incremental_gross - incremental_employee_deductions
        return {
            "gross_amount": currency.round(incremental_gross),
            "employee_deductions": currency.round(incremental_employee_deductions),
            "net_amount": currency.round(incremental_net),
            "employer_contributions": currency.round(incremental_employer_contributions),
            "employer_total_cost": currency.round(incremental_gross + incremental_employer_contributions),
        }

    def _l10n_ar_multiply_amounts(self, amounts, factor, currency):
        return {
            field_name: currency.round(amounts[field_name] * factor)
            for field_name in self._l10n_ar_amount_fields()
        }

    def _l10n_ar_divide_amounts(self, amounts, divisor, currency):
        return {
            field_name: currency.round(amounts[field_name] / divisor) if divisor else 0.0
            for field_name in self._l10n_ar_amount_fields()
        }

    def _l10n_ar_sum_amounts(self, amount_sets, currency):
        result = dict.fromkeys(self._l10n_ar_amount_fields(), 0.0)
        for amounts in amount_sets:
            for field_name in self._l10n_ar_amount_fields():
                result[field_name] += amounts[field_name]
        return {
            field_name: currency.round(result[field_name])
            for field_name in self._l10n_ar_amount_fields()
        }

    def _l10n_ar_simulate_payslip(
        self,
        company,
        employee,
        version,
        structure,
        date_from,
        date_to,
        simulation_context=None,
    ):
        simulation_context = simulation_context or self._l10n_ar_get_simulation_context()
        slip = self.env["hr.payslip"].with_context(simulation_context).create({
            "name": _("Simulación de costos AR"),
            "employee_id": employee.id,
            "company_id": company.id,
            "version_id": version.id,
            "struct_id": structure.id,
            "date_from": date_from,
            "date_to": date_to,
        })
        slip.compute_sheet()
        return slip

    def _l10n_ar_simulate_regular_monthly_amounts(
        self,
        company,
        structure_type,
        reference_date,
        contract_start_date,
        seniority_date,
        wage,
        union_rate=0.0,
        seniority_percent=0.0,
    ):
        regular_structure = structure_type.default_struct_id or self.env.ref(
            "l10n_ar_hr_payroll.l10n_ar_regular_pay"
        )
        simulation_context = self._l10n_ar_get_simulation_context()
        reference_date = fields.Date.to_date(reference_date)
        regular_from = reference_date.replace(day=1)
        regular_to = regular_from + relativedelta(day=31)

        with self.env.cr.savepoint(flush=False) as savepoint:
            temp_employee = self.env["hr.employee"].with_context(simulation_context).create({
                "name": _("Simulación AR"),
                "company_id": company.id,
            })
            temp_version = temp_employee.version_id.with_context(simulation_context)
            temp_version.write({
                "company_id": company.id,
                "structure_type_id": structure_type.id,
                "resource_calendar_id": company.resource_calendar_id.id,
                "contract_date_start": contract_start_date,
                "date_start": contract_start_date,
                "wage": wage,
                "l10n_ar_seniority_date": seniority_date,
                "l10n_ar_seniority_percent": seniority_percent,
                "l10n_ar_union_rate": union_rate,
            })
            regular_slip = self._l10n_ar_simulate_payslip(
                company,
                temp_employee,
                temp_version,
                regular_structure,
                regular_from,
                regular_to,
                simulation_context=simulation_context,
            )
            employer_rate = (
                self._l10n_ar_get_rule_parameter(regular_slip, "l10n_ar_employer_contribution_rate")
                + self._l10n_ar_get_rule_parameter(regular_slip, "l10n_ar_art_rate")
            ) / 100.0
            regular_monthly = self._l10n_ar_extract_component_amounts(
                regular_slip,
                employer_rate=employer_rate,
                employer_from_lines=True,
            )

            self.env.cr.precommit.data.pop("mail.tracking.hr.version", None)
            self.env.cr.precommit.data.pop("mail.tracking.hr.employee", None)
            self.env.flush_all()
            savepoint.rollback()

        self.env["hr.version"].invalidate_model()
        self.env["hr.employee"].invalidate_model()
        self.env["hr.payslip"].invalidate_model()
        return regular_monthly

    def _l10n_ar_simulate_cost_package(
        self,
        company,
        structure_type,
        reference_date,
        contract_start_date,
        seniority_date,
        wage,
        union_rate=0.0,
        seniority_percent=0.0,
    ):
        regular_structure = structure_type.default_struct_id or self.env.ref(
            "l10n_ar_hr_payroll.l10n_ar_regular_pay"
        )
        sac_structure = self.env.ref("l10n_ar_hr_payroll.l10n_ar_sac_pay")
        vacation_structure = self.env.ref("l10n_ar_hr_payroll.l10n_ar_vacation_pay")
        simulation_context = self._l10n_ar_get_simulation_context()

        reference_date = fields.Date.to_date(reference_date)
        regular_from = reference_date.replace(day=1)
        regular_to = regular_from + relativedelta(day=31)
        semester_1_from = date(reference_date.year, 1, 1)
        semester_1_to = date(reference_date.year, 6, 30)
        semester_2_from = date(reference_date.year, 7, 1)
        semester_2_to = date(reference_date.year, 12, 31)
        vacation_from = date(reference_date.year, 1, 1)
        vacation_to = date(reference_date.year, 12, 31)

        with self.env.cr.savepoint(flush=False) as savepoint:
            temp_employee = self.env["hr.employee"].with_context(simulation_context).create({
                "name": _("Simulación AR"),
                "company_id": company.id,
            })
            temp_version = temp_employee.version_id.with_context(simulation_context)
            temp_version.write({
                "company_id": company.id,
                "structure_type_id": structure_type.id,
                "resource_calendar_id": company.resource_calendar_id.id,
                "contract_date_start": contract_start_date,
                "date_start": contract_start_date,
                "wage": wage,
                "l10n_ar_seniority_date": seniority_date,
                "l10n_ar_seniority_percent": seniority_percent,
                "l10n_ar_union_rate": union_rate,
            })

            regular_slip = self._l10n_ar_simulate_payslip(
                company,
                temp_employee,
                temp_version,
                regular_structure,
                regular_from,
                regular_to,
                simulation_context=simulation_context,
            )
            sac_semester_1_slip = self._l10n_ar_simulate_payslip(
                company,
                temp_employee,
                temp_version,
                sac_structure,
                semester_1_from,
                semester_1_to,
                simulation_context=simulation_context,
            )
            sac_semester_2_slip = self._l10n_ar_simulate_payslip(
                company,
                temp_employee,
                temp_version,
                sac_structure,
                semester_2_from,
                semester_2_to,
                simulation_context=simulation_context,
            )
            vacation_slip = self._l10n_ar_simulate_payslip(
                company,
                temp_employee,
                temp_version,
                vacation_structure,
                vacation_from,
                vacation_to,
                simulation_context=simulation_context,
            )

            employer_rate = (
                self._l10n_ar_get_rule_parameter(regular_slip, "l10n_ar_employer_contribution_rate")
                + self._l10n_ar_get_rule_parameter(regular_slip, "l10n_ar_art_rate")
            ) / 100.0
            employee_rate = (
                self._l10n_ar_get_rule_parameter(regular_slip, "l10n_ar_employee_jubilacion_rate")
                + self._l10n_ar_get_rule_parameter(regular_slip, "l10n_ar_employee_ley_19032_rate")
                + self._l10n_ar_get_rule_parameter(regular_slip, "l10n_ar_employee_obra_social_rate")
                + union_rate
            ) / 100.0

            regular_monthly = self._l10n_ar_extract_component_amounts(
                regular_slip,
                employer_rate=employer_rate,
                employer_from_lines=True,
            )
            regular_annual = self._l10n_ar_multiply_amounts(regular_monthly, 12, regular_slip.currency_id)
            sac_annual = self._l10n_ar_sum_amounts(
                [
                    self._l10n_ar_extract_component_amounts(
                        sac_semester_1_slip,
                        employer_rate=employer_rate,
                        employer_from_lines=False,
                    ),
                    self._l10n_ar_extract_component_amounts(
                        sac_semester_2_slip,
                        employer_rate=employer_rate,
                        employer_from_lines=False,
                    ),
                ],
                regular_slip.currency_id,
            )
            vacation_days = vacation_slip._l10n_ar_get_vacation_days()
            vacation_annual = self._l10n_ar_convert_vacation_to_incremental_amounts(
                wage=wage,
                vacation_days=vacation_days,
                vacation_divisor=self._l10n_ar_get_rule_parameter(vacation_slip, "l10n_ar_vacation_divisor") or 25.0,
                employee_rate=employee_rate,
                employer_rate=employer_rate,
                currency=regular_slip.currency_id,
            )
            annual_total = self._l10n_ar_sum_amounts(
                [regular_annual, sac_annual, vacation_annual],
                regular_slip.currency_id,
            )
            monthly_prorated_total = self._l10n_ar_divide_amounts(
                annual_total,
                12.0,
                regular_slip.currency_id,
            )

            self.env.cr.precommit.data.pop("mail.tracking.hr.version", None)
            self.env.cr.precommit.data.pop("mail.tracking.hr.employee", None)
            self.env.flush_all()
            savepoint.rollback()

        self.env["hr.version"].invalidate_model()
        self.env["hr.employee"].invalidate_model()
        self.env["hr.payslip"].invalidate_model()

        return {
            "regular_monthly": regular_monthly,
            "regular_annual": regular_annual,
            "sac_annual": sac_annual,
            "vacation_annual": vacation_annual,
            "annual_total": annual_total,
            "monthly_prorated_total": monthly_prorated_total,
        }

    def _l10n_ar_get_monthly_breakdown(
        self,
        company,
        structure_type,
        contract_start_date,
        seniority_date,
        reference_date,
        wage,
        union_rate=0.0,
        seniority_percent=0.0,
    ):
        if company.country_code != "AR":
            raise ValidationError(_("El servicio de costeo local está disponible solo para compañías de Argentina."))
        cost_package = self._l10n_ar_simulate_cost_package(
            company=company,
            structure_type=structure_type,
            reference_date=reference_date,
            contract_start_date=contract_start_date,
            seniority_date=seniority_date,
            wage=wage,
            union_rate=union_rate,
            seniority_percent=seniority_percent,
        )
        currency = company.currency_id
        sac_monthly = self._l10n_ar_divide_amounts(cost_package["sac_annual"], 12.0, currency)
        vacation_monthly = self._l10n_ar_divide_amounts(cost_package["vacation_annual"], 12.0, currency)
        monthly_cost_company = currency.round(
            cost_package["regular_monthly"]["gross_amount"]
            + cost_package["regular_monthly"]["employer_contributions"]
            + sac_monthly["employer_total_cost"]
            + vacation_monthly["employer_total_cost"]
        )
        return {
            "monthly_cost_company": monthly_cost_company,
            "regular_monthly_company": cost_package["regular_monthly"]["gross_amount"],
            "employer_contributions_monthly_company": cost_package["regular_monthly"]["employer_contributions"],
            "sac_monthly_company": sac_monthly["employer_total_cost"],
            "vacation_monthly_company": vacation_monthly["employer_total_cost"],
        }
