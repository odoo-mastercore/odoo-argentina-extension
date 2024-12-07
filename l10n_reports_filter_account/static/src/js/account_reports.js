odoo.define('l10n_reports_filter_account.account_report', function (require) {
    'use strict';


    var core = require('web.core');
    var data = require('web.data');
    var Widget = require('web.Widget');
    var QWeb = core.qweb;
    var _t = core._t;

    var AccountReportWidget = require('account_reports.account_report');

    AccountReportWidget.include({

        render_searchview_buttons: function() {
            var self = this;

            _.each(this.$searchview_buttons.find('.account_account_filter'), function(k) {
                $(k).toggleClass('selected', (_.filter(self.report_options[$(k).data('filter')], function(el){return ''+el.id == ''+$(k).data('id') && el.selected === true;})).length > 0);
            });
            //console.log('render_searchview_buttons-this: ', this);
            //console.log('render_searchview_buttons-report_options: ', this.report_options);
            this._super.apply(this, arguments);
            this.$searchview_buttons.find('.exclude_companies_without_difference').click(function (event) {
                var option_value = $(this).data('filter');
                self.report_options.exclude_companies_without_difference = $('input[name="exclude_companies_without_difference"]').prop('checked');
                _.filter(self.report_options[option_value], function(el) {
                    el.selected = false;
                    self.odoo_context['exclude_companies_without_difference'] = $('input[name="exclude_companies_without_difference"]').prop('checked');
                    return el;
                });
                self.reload();
            });
            this.$searchview_buttons.find('.account_account_filter').click(function (event) {
                //console.log('account_account_filter-click-this: ', this);
                var option_value = $(this).data('filter');
                var option_id = $(this).data('id');
                //console.log('account_account_filter-click-title: ',  $(this).attr('title'));
                $('#div_account_acc_ids').before('<div class="badge badge-pill  o_tag_color_0" data-color="0" data-index="0" t-att-id="badge_'+option_id+'" title="Tag color: No color"><span class="o_badge_text" title="3DF SRL"><span role="img" aria-label="Tag color: No color"></span><span class="o_tag_badge_text acc_acc_value" val="'+option_id+'">'+  $(this).attr('title')+ '</span></span><a href="#" class="fa fa-times o_delete o_delete_acc" title="Suprimir" aria-label="Suprimir"></a></div>')
                //console.log('account_account_filter-click-option_value: ', option_value);
                //console.log('account_account_filter-click-option_id: ', option_id);
                var account_ids = [];
                var account_acc_ids = [];
                $.each($('.acc_acc_value'), function() {
                    //console.log('account_account_filter-click-e: ', $(this).attr('val'));
                    account_ids.push($(this).attr('val'));
                    var option = {};
                    option['id'] = $(this).attr('val');
                    option['name'] = $(this).text();
                    account_acc_ids.push(option);
                });
                //console.log('account_account_filter-click-account_ids: ', account_ids);
                //console.log('account_account_filter-click-account_acc_ids: ', account_acc_ids);
                self.report_options.account_acc_ids = account_ids;
                self.report_options.account_account_ids = account_acc_ids;
                _.filter(self.report_options[option_value], function(el) {
                    el.selected = false;
                    self.odoo_context['account_acc_ids'] = account_ids
                    self.odoo_context['account_account_ids'] = account_acc_ids
                    return el;
                });
                self.reload();
            });
            this.$searchview_buttons.find('.o_delete_acc').click(function (event) {
                //console.log('o_delete_acc-click-this: ', this);
                //console.log('o_delete_acc-click-this: ', $(this).parent());
                $(this).parent().remove();
                var account_ids = [];
                var account_acc_ids = [];
                $.each($('.acc_acc_value'), function() {
                    //console.log('account_account_filter-click-e: ', $(this).attr('val'));
                    account_ids.push($(this).attr('val'));
                    var option = {};
                    option['id'] = $(this).attr('val');
                    option['name'] = $(this).text();
                    account_acc_ids.push(option);
                });
                //console.log('account_account_filter-click-account_ids: ', account_ids);
                //console.log('account_account_filter-click-account_acc_ids: ', account_acc_ids);
                self.report_options.account_acc_ids = account_ids;
                self.report_options.account_account_ids = account_acc_ids;
                _.filter(self.report_options['account_accounts'], function(el) {
                    el.selected = false;
                    self.odoo_context['account_acc_ids'] = account_ids
                    self.odoo_context['account_account_ids'] = account_acc_ids
                    return el;
                });
                self.reload();
            });

        }
    });
});