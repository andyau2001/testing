odoo.define('pos_invoice_prefix.payment_button', function (require) {
    'use strict';

    const {Gui} = require('point_of_sale.Gui');
    const PosComponent = require('point_of_sale.PosComponent');
    const {posbus} = require('point_of_sale.utils');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    var core = require('web.core');

    const CustomButtonPaymentScreen = (PaymentScreen) =>
        class extends PaymentScreen {
            constructor() {
                super(...arguments);
            }

            async IsCustomButton() {
                var now = new Date();
                var month = (now.getMonth() + 1);
                var day = now.getDate();
                if (month < 10)
                    month = "0" + month;
                if (day < 10)
                    day = "0" + day;
                var today = now.getFullYear() + '-' + month + '-' + day;
                $('#invoice_date').val(today);

                document.getElementById('myModal').style.display = 'block';
                var selection = await this.rpc({
                    model: 'account.move',
                    method: 'get_all_prefix',
                });
                var selectionArr = JSON.parse(selection);
                var output = [];
                $.each(selectionArr, function(key, value)
                {
                    output.push('<option value="'+ key +'">'+ value +'</option>');
                });
                $('#invoice_prefix').html(output.join(''));
            }

            async closeButton() {
                //invoice prefix
                var prefix = $('#invoice_prefix').val();
                this.env.pos.pos_order_prefix = prefix;
                this.env.pos.get_order().set_prefix(prefix);

                //invoice date
                var date = $('#invoice_date').val();
                this.env.pos.pos_order_date = date;
                this.env.pos.get_order().set_date(date);

                //invoice remark
                var remark = $('#remark').val();
                this.env.pos.pos_order_remark = remark;
                this.env.pos.get_order().set_remark(remark);

                //invoice remark internal
                var remark_internal = $('#remark_internal').val();
                this.env.pos.pos_order_remark_internal = remark_internal;
                this.env.pos.get_order().set_remark_internal(remark_internal);

                document.getElementById('myModal').style.display = 'none';
            }
        };

    Registries.Component.extend(PaymentScreen, CustomButtonPaymentScreen);
    return CustomButtonPaymentScreen;
});