# l10n_ar_hr_payroll

Initial payroll localization module for Argentina on Odoo 19.

## Scope in this first iteration

- Employee and contract fields:
  - `CUIL` validation and normalization.
  - Seniority date and seniority rate.
  - Union contribution rate.
- Payroll structures:
  - Regular payroll.
  - SAC payroll.
  - Paid vacations payroll.
- Salary rules:
  - Basic salary and seniority allowance.
  - Employee deductions: jubilacion, Ley 19032, obra social, union.
  - Employer costs: social security contribution and ART.
  - Net salary computation.
- Rule parameters:
  - Legal percentages and divisors are parameterized through `hr.rule.parameter`.
- Cost simulator wizard:
  - New hire cost simulation (employee net + employer contributions).
  - Salary increase simulation from employee form.
  - Includes regular payroll, SAC and paid vacation components.

## Legal basis used

- LCT 20.744 (SAC arts. 121-123; vacations arts. 150-157): [Argentina.gob.ar](https://www.argentina.gob.ar/normativa/nacional/25552/texact)
- Employee pension contribution 11% (SIPA): Law 24.241 art. 11.
- INSSJP (Ley 19.032) contribution references.
- Employer contribution reference rate (20.4% / special cases): ARCA social security guidance.

## Important note

This module is a technical baseline. In Argentina, final payroll implementation usually requires:

- Collective agreement (CCT) specific rules.
- Sector/company specific additional items.
- Periodic legal and tax updates.

Always validate rates and formulas with payroll/accounting advisors before production payroll.
