/** @odoo-module **/
import { registry } from '@web/core/registry'
import { useService } from "@web/core/utils/hooks";

const {Component} = owl

export class NavbarMenu extends Component {
    setup(){
        super.setup()
        this.orm = useService("orm");
        this._getCurrencyRateData();
        this.show_dropdown = false;
    };

    async _getCurrencyRateData(){
        var self = this;
        const response = await this.orm.call('res.currency', 'currency_rate_navbar',[[]])
        var currency_list = []
        if(response){
            response.forEach(element => {
                currency_list.push(element)
            });
            this.currencys = currency_list
        }
    }
    onClickNavbarMenu(){
        const dropdown_content = document.getElementById("dropdown-bcv-currencies");
        if(!this.show_dropdown){
            this._MountRates()
            this.show_dropdown = true
            dropdown_content.style="display: block;"
        }else{
            this._RemoveRates()
            this.show_dropdown = false
            dropdown_content.style="display:none"
        }
    }
    _MountRates(){
        const dropdown_content = document.getElementById("dropdown-bcv-currencies");
        this.currencys.forEach(element =>{
            var anchor = document.createElement("a");
            anchor.textContent = element.name + ": " + element.rate;
            console.log(dropdown_content)
            dropdown_content.appendChild(anchor);
        })
    }
    _RemoveRates(){
        const dropdown_content = document.getElementById("dropdown-bcv-currencies");
        while (dropdown_content.firstChild) {
            dropdown_content.removeChild(dropdown_content.firstChild);
          }
    }
}

Object.assign(NavbarMenu,{
    template: 'bcvCurrencyRateMenu'
})

registry.category('systray').add('l10n_ve_currency_rate_bcv.NavbarMenu', {Component: NavbarMenu}, {sequence: 30});