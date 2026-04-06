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

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class L10nArHrPayrollCostSimulatorWizard(models.TransientModel):
    _name = "l10n.ar.hr.payroll.cost.simulator.wizard"
    _description = "AR Payroll Cost Simulator"

    mode = fields.Selection(
        selection=[
            ("new_hire", "Alta de empleado"),
            ("salary_increase", "Incremento salarial"),
        ],
        string="Modo",
        default="new_hire",
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )
    structure_type_id = fields.Many2one(
        "hr.payroll.structure.type",
        string="Tipo de estructura",
        required=True,
        default=lambda self: self._l10n_ar_default_structure_type_id(),
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado",
        domain="[('company_id', '=', company_id)]",
    )
    reference_year = fields.Integer(
        string="Año de simulación",
        required=True,
        default=lambda self: fields.Date.today().year,
    )
    contract_start_date = fields.Date(
        string="Fecha de ingreso",
        required=True,
        default=lambda self: fields.Date.today() + relativedelta(day=1),
    )
    seniority_date = fields.Date(
        string="Fecha de antigüedad",
        required=True,
        default=lambda self: fields.Date.today() + relativedelta(day=1),
    )

    current_gross_monthly = fields.Monetary(string="Bruto mensual actual")
    proposed_input_type = fields.Selection(
        selection=[
            ("gross", "Bruto mensual"),
            ("net", "Neto regular mensual"),
        ],
        string="Entrada propuesta",
        default="gross",
        required=True,
    )
    proposed_gross_monthly = fields.Monetary(string="Bruto mensual propuesto")
    proposed_net_regular_monthly = fields.Monetary(string="Neto regular mensual propuesto")

    current_union_rate = fields.Float(string="Aporte sindical actual (%)")
    proposed_union_rate = fields.Float(string="Aporte sindical propuesto (%)", default=0.0)

    current_seniority_percent = fields.Float(string="Antigüedad actual (%)")
    proposed_seniority_percent = fields.Float(string="Antigüedad propuesta (%)", default=0.0)

    result_ready = fields.Boolean(string="Resultado listo", default=False)
    line_ids = fields.One2many(
        "l10n.ar.hr.payroll.cost.simulator.line",
        "wizard_id",
        string="Detalle",
        copy=False,
    )

    current_regular_monthly_cost = fields.Monetary(string="Costo regular mensual actual")
    proposed_regular_monthly_cost = fields.Monetary(string="Costo regular mensual propuesto")
    delta_regular_monthly_cost = fields.Monetary(string="Delta costo regular mensual")

    current_regular_annual_cost = fields.Monetary(string="Costo anual regular actual")
    proposed_regular_annual_cost = fields.Monetary(string="Costo anual regular propuesto")
    delta_regular_annual_cost = fields.Monetary(string="Delta costo anual regular")

    current_sac_annual_cost = fields.Monetary(string="Costo anual SAC actual")
    proposed_sac_annual_cost = fields.Monetary(string="Costo anual SAC propuesto")
    delta_sac_annual_cost = fields.Monetary(string="Delta costo anual SAC")

    current_vacation_annual_cost = fields.Monetary(string="Costo anual vacaciones actual")
    proposed_vacation_annual_cost = fields.Monetary(string="Costo anual vacaciones propuesto")
    delta_vacation_annual_cost = fields.Monetary(string="Delta costo anual vacaciones")

    current_prorated_monthly_cost = fields.Monetary(string="Costo mensual prorrateado actual")
    proposed_prorated_monthly_cost = fields.Monetary(string="Costo mensual prorrateado propuesto")
    delta_prorated_monthly_cost = fields.Monetary(string="Delta costo mensual prorrateado")

    current_annual_total_cost = fields.Monetary(string="Costo anual total actual")
    proposed_annual_total_cost = fields.Monetary(string="Costo anual total propuesto")
    delta_annual_total_cost = fields.Monetary(string="Delta costo anual total")

    current_regular_monthly_net = fields.Monetary(string="Neto regular mensual actual")
    proposed_regular_monthly_net = fields.Monetary(string="Neto regular mensual propuesto")
    delta_regular_monthly_net = fields.Monetary(string="Delta neto regular mensual")

    current_prorated_monthly_net = fields.Monetary(string="Neto mensual prorrateado actual")
    proposed_prorated_monthly_net = fields.Monetary(string="Neto mensual prorrateado propuesto")
    delta_prorated_monthly_net = fields.Monetary(string="Delta neto mensual prorrateado")

    current_annual_total_net = fields.Monetary(string="Neto anual total actual")
    proposed_annual_total_net = fields.Monetary(string="Neto anual total propuesto")
    delta_annual_total_net = fields.Monetary(string="Delta neto anual total")

    @api.model
    def _l10n_ar_default_structure_type_id(self):
        return self.env.ref("l10n_ar_hr_payroll.l10n_ar_employee", raise_if_not_found=False)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if not values.get("structure_type_id"):
            default_structure_type = self._l10n_ar_default_structure_type_id()
            if default_structure_type:
                values["structure_type_id"] = default_structure_type.id

        employee_id = self.env.context.get("default_employee_id")
        mode = values.get("mode") or self.env.context.get("default_mode")
        if employee_id and mode == "salary_increase":
            employee = self.env["hr.employee"].browse(employee_id).exists()
            if employee:
                version = employee.version_id
                structure_type = version.structure_type_id or self._l10n_ar_default_structure_type_id()
                values.update({
                    "employee_id": employee.id,
                    "company_id": employee.company_id.id,
                    "structure_type_id": structure_type.id if structure_type else False,
                    "contract_start_date": version.contract_date_start or version.date_start or values.get("contract_start_date"),
                    "seniority_date": (
                        version.l10n_ar_seniority_date
                        or version.contract_date_start
                        or version.date_start
                        or values.get("seniority_date")
                    ),
                    "current_gross_monthly": version.wage,
                    "proposed_gross_monthly": version.wage,
                    "current_union_rate": version.l10n_ar_union_rate,
                    "proposed_union_rate": version.l10n_ar_union_rate,
                    "current_seniority_percent": version.l10n_ar_seniority_percent,
                    "proposed_seniority_percent": version.l10n_ar_seniority_percent,
                })
        return values

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        if not self.employee_id:
            return
        version = self.employee_id.version_id
        self.company_id = self.employee_id.company_id
        self.structure_type_id = version.structure_type_id or self._l10n_ar_default_structure_type_id()
        self.contract_start_date = version.contract_date_start or version.date_start or self.contract_start_date
        self.seniority_date = (
            version.l10n_ar_seniority_date
            or version.contract_date_start
            or version.date_start
            or self.contract_start_date
        )
        self.current_gross_monthly = version.wage
        self.proposed_gross_monthly = version.wage
        self.current_union_rate = version.l10n_ar_union_rate
        self.proposed_union_rate = version.l10n_ar_union_rate
        self.current_seniority_percent = version.l10n_ar_seniority_percent
        self.proposed_seniority_percent = version.l10n_ar_seniority_percent

    @api.constrains("proposed_union_rate", "current_union_rate", "proposed_seniority_percent", "current_seniority_percent")
    def _check_rate_ranges(self):
        for wizard in self:
            for value, label in (
                (wizard.proposed_union_rate, _("aporte sindical propuesto")),
                (wizard.current_union_rate, _("aporte sindical actual")),
                (wizard.proposed_seniority_percent, _("porcentaje por antigüedad propuesto")),
                (wizard.current_seniority_percent, _("porcentaje por antigüedad actual")),
            ):
                if value < 0 or value > 100:
                    raise ValidationError(_("El valor de %s debe estar entre 0 y 100.") % label)

    def action_simulate(self):
        self.ensure_one()
        self._l10n_ar_validate_inputs()
        if self.proposed_input_type == "net":
            self.proposed_gross_monthly = self._l10n_ar_resolve_gross_from_target_net_regular_monthly(
                target_net=self.proposed_net_regular_monthly,
                union_rate=self.proposed_union_rate,
                seniority_percent=self.proposed_seniority_percent,
            )
        self.line_ids.unlink()
        summary_vals = self._l10n_ar_get_empty_summary_vals()

        proposed_results = self._l10n_ar_simulate_cost_package(
            wage=self.proposed_gross_monthly,
            union_rate=self.proposed_union_rate,
            seniority_percent=self.proposed_seniority_percent,
        )
        self._l10n_ar_update_summary_for_scenario(summary_vals, "proposed", proposed_results)
        line_commands = self._l10n_ar_build_line_commands("proposed", proposed_results)

        current_results = False
        if self.mode == "salary_increase":
            current_results = self._l10n_ar_simulate_cost_package(
                wage=self.current_gross_monthly,
                union_rate=self.current_union_rate,
                seniority_percent=self.current_seniority_percent,
            )
            self._l10n_ar_update_summary_for_scenario(summary_vals, "current", current_results)
            line_commands += self._l10n_ar_build_line_commands("current", current_results)
            self._l10n_ar_update_summary_deltas(summary_vals)

        summary_vals["result_ready"] = True
        self.write(summary_vals)
        if line_commands:
            self.write({"line_ids": line_commands})
        return self._l10n_ar_reopen_wizard()

    def _l10n_ar_reopen_wizard(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "l10n_ar_hr_payroll.action_l10n_ar_cost_simulator_wizard"
        )
        action["res_id"] = self.id
        action["target"] = "new"
        return action

    def _l10n_ar_validate_inputs(self):
        self.ensure_one()
        if self.company_id.country_code != "AR":
            raise UserError(_("El simulador está disponible solo para compañías de Argentina."))
        if self.reference_year < 2000 or self.reference_year > 9999:
            raise ValidationError(_("El año de simulación debe estar entre 2000 y 9999."))
        if self.proposed_input_type == "gross" and self.proposed_gross_monthly <= 0:
            raise ValidationError(_("El salario bruto propuesto debe ser mayor a cero."))
        if self.proposed_input_type == "net" and self.proposed_net_regular_monthly <= 0:
            raise ValidationError(_("El neto regular mensual propuesto debe ser mayor a cero."))
        if self.mode == "salary_increase":
            if not self.employee_id:
                raise ValidationError(_("Debe seleccionar un empleado para simular incremento salarial."))
            if self.current_gross_monthly <= 0:
                raise ValidationError(_("El salario bruto actual debe ser mayor a cero."))
            if self.employee_id.company_country_code != "AR":
                raise ValidationError(_("El empleado seleccionado no pertenece a una compañía de Argentina."))
        if not self.structure_type_id:
            raise ValidationError(_("Debe seleccionar un tipo de estructura salarial."))
        if not self.contract_start_date:
            raise ValidationError(_("Debe indicar una fecha de ingreso para la simulación."))
        if not self.seniority_date:
            raise ValidationError(_("Debe indicar una fecha de antigüedad para la simulación."))

    def _l10n_ar_get_simulation_context(self):
        self.ensure_one()
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

    def _l10n_ar_resolve_gross_from_target_net_regular_monthly(self, target_net, union_rate, seniority_percent):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        cache = {}

        def _get_net_for_gross(gross_amount):
            rounded_gross = currency.round(gross_amount)
            if rounded_gross not in cache:
                regular_monthly = self._l10n_ar_simulate_regular_monthly_amounts(
                    wage=rounded_gross,
                    union_rate=union_rate,
                    seniority_percent=seniority_percent,
                )
                cache[rounded_gross] = regular_monthly["net_amount"]
            return cache[rounded_gross]

        low = 0.0
        high = max(target_net, 1.0)
        high_net = _get_net_for_gross(high)
        for _idx in range(12):
            if high_net >= target_net:
                break
            low = high
            high *= 1.35
            high_net = _get_net_for_gross(high)

        if high_net < target_net:
            raise ValidationError(
                _("No fue posible derivar un bruto mensual para el neto objetivo con los parámetros actuales.")
            )

        for _idx in range(24):
            mid = (low + high) / 2.0
            mid_net = _get_net_for_gross(mid)
            if mid_net < target_net:
                low = mid
            else:
                high = mid
        return currency.round(high)

    def _l10n_ar_simulate_regular_monthly_amounts(self, wage, union_rate, seniority_percent):
        self.ensure_one()
        regular_structure = self.structure_type_id.default_struct_id or self.env.ref(
            "l10n_ar_hr_payroll.l10n_ar_regular_pay"
        )
        simulation_context = self._l10n_ar_get_simulation_context()
        current_month = fields.Date.today().month
        regular_from = date(self.reference_year, current_month, 1)
        regular_to = regular_from + relativedelta(day=31)

        with self.env.cr.savepoint(flush=False) as savepoint:
            temp_employee = self.env["hr.employee"].with_context(simulation_context).create({
                "name": _("Simulación AR"),
                "company_id": self.company_id.id,
            })
            temp_version = temp_employee.version_id.with_context(simulation_context)
            temp_version.write({
                "company_id": self.company_id.id,
                "structure_type_id": self.structure_type_id.id,
                "resource_calendar_id": self.company_id.resource_calendar_id.id,
                "contract_date_start": self.contract_start_date,
                "date_start": self.contract_start_date,
                "wage": wage,
                "l10n_ar_seniority_date": self.seniority_date,
                "l10n_ar_seniority_percent": seniority_percent,
                "l10n_ar_union_rate": union_rate,
            })
            regular_slip = self._l10n_ar_simulate_payslip(
                temp_employee, temp_version, regular_structure, regular_from, regular_to
            )
            employer_rate = (
                self._l10n_ar_get_rule_parameter(regular_slip, "l10n_ar_employer_contribution_rate")
                + self._l10n_ar_get_rule_parameter(regular_slip, "l10n_ar_art_rate")
            ) / 100.0
            regular_monthly = self._l10n_ar_extract_component_amounts(
                regular_slip, employer_rate=employer_rate, employer_from_lines=True
            )

            self.env.cr.precommit.data.pop("mail.tracking.hr.version", None)
            self.env.cr.precommit.data.pop("mail.tracking.hr.employee", None)
            self.env.flush_all()
            savepoint.rollback()

        self.env["hr.version"].invalidate_model()
        self.env["hr.employee"].invalidate_model()
        self.env["hr.payslip"].invalidate_model()
        return regular_monthly

    def _l10n_ar_simulate_cost_package(self, wage, union_rate, seniority_percent):
        self.ensure_one()
        regular_structure = self.structure_type_id.default_struct_id or self.env.ref(
            "l10n_ar_hr_payroll.l10n_ar_regular_pay"
        )
        sac_structure = self.env.ref("l10n_ar_hr_payroll.l10n_ar_sac_pay")
        vacation_structure = self.env.ref("l10n_ar_hr_payroll.l10n_ar_vacation_pay")
        simulation_context = self._l10n_ar_get_simulation_context()

        current_month = fields.Date.today().month
        regular_from = date(self.reference_year, current_month, 1)
        regular_to = regular_from + relativedelta(day=31)
        semester_1_from = date(self.reference_year, 1, 1)
        semester_1_to = date(self.reference_year, 6, 30)
        semester_2_from = date(self.reference_year, 7, 1)
        semester_2_to = date(self.reference_year, 12, 31)
        vacation_from = date(self.reference_year, 1, 1)
        vacation_to = date(self.reference_year, 12, 31)

        with self.env.cr.savepoint(flush=False) as savepoint:
            temp_employee = self.env["hr.employee"].with_context(simulation_context).create({
                "name": _("Simulación AR"),
                "company_id": self.company_id.id,
            })
            temp_version = temp_employee.version_id.with_context(simulation_context)
            temp_version.write({
                "company_id": self.company_id.id,
                "structure_type_id": self.structure_type_id.id,
                "resource_calendar_id": self.company_id.resource_calendar_id.id,
                "contract_date_start": self.contract_start_date,
                "date_start": self.contract_start_date,
                "wage": wage,
                "l10n_ar_seniority_date": self.seniority_date,
                "l10n_ar_seniority_percent": seniority_percent,
                "l10n_ar_union_rate": union_rate,
            })

            regular_slip = self._l10n_ar_simulate_payslip(
                temp_employee, temp_version, regular_structure, regular_from, regular_to
            )
            sac_semester_1_slip = self._l10n_ar_simulate_payslip(
                temp_employee, temp_version, sac_structure, semester_1_from, semester_1_to
            )
            sac_semester_2_slip = self._l10n_ar_simulate_payslip(
                temp_employee, temp_version, sac_structure, semester_2_from, semester_2_to
            )
            vacation_slip = self._l10n_ar_simulate_payslip(
                temp_employee, temp_version, vacation_structure, vacation_from, vacation_to
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
                regular_slip, employer_rate=employer_rate, employer_from_lines=True
            )
            regular_annual = self._l10n_ar_multiply_amounts(regular_monthly, 12, regular_slip.currency_id)
            sac_annual = self._l10n_ar_sum_amounts(
                [
                    self._l10n_ar_extract_component_amounts(
                        sac_semester_1_slip, employer_rate=employer_rate, employer_from_lines=False
                    ),
                    self._l10n_ar_extract_component_amounts(
                        sac_semester_2_slip, employer_rate=employer_rate, employer_from_lines=False
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
                [regular_annual, sac_annual, vacation_annual], regular_slip.currency_id
            )
            monthly_prorated_total = self._l10n_ar_divide_amounts(
                annual_total, 12.0, regular_slip.currency_id
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

    def _l10n_ar_simulate_payslip(self, employee, version, structure, date_from, date_to):
        slip = self.env["hr.payslip"].with_context(self._l10n_ar_get_simulation_context()).create({
            "name": _("Simulación de costos AR"),
            "employee_id": employee.id,
            "company_id": self.company_id.id,
            "version_id": version.id,
            "struct_id": structure.id,
            "date_from": date_from,
            "date_to": date_to,
        })
        slip.compute_sheet()
        return slip

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

    def _l10n_ar_get_payslip_line_total(self, payslip, code):
        line = payslip.line_ids.filtered(lambda payslip_line: payslip_line.code == code)[:1]
        return line.total if line else 0.0

    def _l10n_ar_get_rule_parameter(self, payslip, code):
        value = payslip._rule_parameter(code) or 0.0
        return float(value)

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

    def _l10n_ar_amount_fields(self):
        return (
            "gross_amount",
            "employee_deductions",
            "net_amount",
            "employer_contributions",
            "employer_total_cost",
        )

    def _l10n_ar_build_line_commands(self, scenario, result_values):
        self.ensure_one()
        lines = [
            (10, _("Regular mensual"), "regular", "monthly", result_values["regular_monthly"]),
            (20, _("Regular anual"), "regular", "annual", result_values["regular_annual"]),
            (30, _("SAC"), "sac", "annual", result_values["sac_annual"]),
            (40, _("Vacaciones (adicional anual)"), "vacation", "annual", result_values["vacation_annual"]),
            (50, _("Total mensual prorrateado"), "total", "monthly", result_values["monthly_prorated_total"]),
            (60, _("Total anual"), "total", "annual", result_values["annual_total"]),
        ]
        commands = []
        for sequence, name, component, periodicity, values in lines:
            commands.append((0, 0, {
                "sequence": sequence,
                "name": name,
                "scenario": scenario,
                "component": component,
                "periodicity": periodicity,
                "gross_amount": values["gross_amount"],
                "employee_deductions": values["employee_deductions"],
                "net_amount": values["net_amount"],
                "employer_contributions": values["employer_contributions"],
                "employer_total_cost": values["employer_total_cost"],
            }))
        return commands

    def _l10n_ar_update_summary_for_scenario(self, summary_vals, prefix, result_values):
        summary_vals.update({
            f"{prefix}_regular_monthly_cost": result_values["regular_monthly"]["employer_total_cost"],
            f"{prefix}_regular_annual_cost": result_values["regular_annual"]["employer_total_cost"],
            f"{prefix}_sac_annual_cost": result_values["sac_annual"]["employer_total_cost"],
            f"{prefix}_vacation_annual_cost": result_values["vacation_annual"]["employer_total_cost"],
            f"{prefix}_prorated_monthly_cost": result_values["monthly_prorated_total"]["employer_total_cost"],
            f"{prefix}_annual_total_cost": result_values["annual_total"]["employer_total_cost"],
            f"{prefix}_regular_monthly_net": result_values["regular_monthly"]["net_amount"],
            f"{prefix}_prorated_monthly_net": result_values["monthly_prorated_total"]["net_amount"],
            f"{prefix}_annual_total_net": result_values["annual_total"]["net_amount"],
        })

    def _l10n_ar_update_summary_deltas(self, summary_vals):
        summary_vals.update({
            "delta_regular_monthly_cost": summary_vals["proposed_regular_monthly_cost"] - summary_vals["current_regular_monthly_cost"],
            "delta_regular_annual_cost": summary_vals["proposed_regular_annual_cost"] - summary_vals["current_regular_annual_cost"],
            "delta_sac_annual_cost": summary_vals["proposed_sac_annual_cost"] - summary_vals["current_sac_annual_cost"],
            "delta_vacation_annual_cost": summary_vals["proposed_vacation_annual_cost"] - summary_vals["current_vacation_annual_cost"],
            "delta_prorated_monthly_cost": summary_vals["proposed_prorated_monthly_cost"] - summary_vals["current_prorated_monthly_cost"],
            "delta_annual_total_cost": summary_vals["proposed_annual_total_cost"] - summary_vals["current_annual_total_cost"],
            "delta_regular_monthly_net": summary_vals["proposed_regular_monthly_net"] - summary_vals["current_regular_monthly_net"],
            "delta_prorated_monthly_net": summary_vals["proposed_prorated_monthly_net"] - summary_vals["current_prorated_monthly_net"],
            "delta_annual_total_net": summary_vals["proposed_annual_total_net"] - summary_vals["current_annual_total_net"],
        })

    def _l10n_ar_get_empty_summary_vals(self):
        return {
            "result_ready": False,
            "current_regular_monthly_cost": 0.0,
            "proposed_regular_monthly_cost": 0.0,
            "delta_regular_monthly_cost": 0.0,
            "current_regular_annual_cost": 0.0,
            "proposed_regular_annual_cost": 0.0,
            "delta_regular_annual_cost": 0.0,
            "current_sac_annual_cost": 0.0,
            "proposed_sac_annual_cost": 0.0,
            "delta_sac_annual_cost": 0.0,
            "current_vacation_annual_cost": 0.0,
            "proposed_vacation_annual_cost": 0.0,
            "delta_vacation_annual_cost": 0.0,
            "current_prorated_monthly_cost": 0.0,
            "proposed_prorated_monthly_cost": 0.0,
            "delta_prorated_monthly_cost": 0.0,
            "current_annual_total_cost": 0.0,
            "proposed_annual_total_cost": 0.0,
            "delta_annual_total_cost": 0.0,
            "current_regular_monthly_net": 0.0,
            "proposed_regular_monthly_net": 0.0,
            "delta_regular_monthly_net": 0.0,
            "current_prorated_monthly_net": 0.0,
            "proposed_prorated_monthly_net": 0.0,
            "delta_prorated_monthly_net": 0.0,
            "current_annual_total_net": 0.0,
            "proposed_annual_total_net": 0.0,
            "delta_annual_total_net": 0.0,
        }


class L10nArHrPayrollCostSimulatorLine(models.TransientModel):
    _name = "l10n.ar.hr.payroll.cost.simulator.line"
    _description = "AR Payroll Cost Simulator Line"
    _order = "scenario, sequence, id"

    wizard_id = fields.Many2one(
        "l10n.ar.hr.payroll.cost.simulator.wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Componente", required=True)
    scenario = fields.Selection(
        selection=[
            ("current", "Actual"),
            ("proposed", "Propuesto"),
        ],
        string="Escenario",
        required=True,
    )
    component = fields.Selection(
        selection=[
            ("regular", "Regular"),
            ("sac", "SAC"),
            ("vacation", "Vacaciones"),
            ("total", "Total"),
        ],
        string="Tipo",
        required=True,
    )
    periodicity = fields.Selection(
        selection=[
            ("monthly", "Mensual"),
            ("annual", "Anual"),
        ],
        string="Período",
        required=True,
    )
    currency_id = fields.Many2one(related="wizard_id.currency_id", readonly=True)
    gross_amount = fields.Monetary(string="Bruto")
    employee_deductions = fields.Monetary(string="Deducciones empleado")
    net_amount = fields.Monetary(string="Neto")
    employer_contributions = fields.Monetary(string="Contribuciones empleador")
    employer_total_cost = fields.Monetary(string="Costo empleador")
