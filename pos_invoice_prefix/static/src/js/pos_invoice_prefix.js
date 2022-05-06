odoo.define('pos_invoice_prefix.invoice_prefix', function(require) {
	"use strict";

	const models = require('point_of_sale.models');
	const core = require('web.core');
	const gui = require('point_of_sale.Gui');
	const utils = require('web.utils');
	const _t = core._t;
	const round_di = utils.round_decimals;
	const round_pr = utils.round_precision;
	const QWeb = core.qweb;
	const field_utils = require('web.field_utils');

	var _super = models.Order.prototype;
	models.Order = models.Order.extend({
		initialize: function(attr, options) {
			_super.initialize.call(this, attr, options);
		},

		export_as_JSON: function() {
			var json = _super.export_as_JSON.apply(this, arguments);
			json.pos_order_prefix = this.pos_order_prefix || this.pos.pos_order_prefix || '';
			json.pos_order_date = this.pos_order_date || this.pos.pos_order_date || '';
			json.pos_order_remark = this.pos_order_remark || this.pos.pos_order_remark || '';
			json.pos_order_remark_internal = this.pos_order_remark_internal || this.pos.pos_order_remark_internal || '';
			return json;
		},

		set_prefix: function(value) {
			this.pos_order_prefix = value;
		},

		set_date: function(value) {
			this.pos_order_date = value;
		},

		set_remark: function(value) {
			this.pos_order_remark = value;
		},

		set_remark_internal: function(value) {
			this.pos_order_remark_internal = value;
		},
	});
});