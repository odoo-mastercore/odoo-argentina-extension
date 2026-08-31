/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { AccountReportFilters } from "@account_reports/components/account_report/filters/filters";

patch(AccountReportFilters.prototype, {
    get hasUIFilter() {
        return (
            super.hasUIFilter || this.controller.filters.show_exclude_zero_balance !== "never"
        );
    },
});