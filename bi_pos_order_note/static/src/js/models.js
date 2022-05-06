odoo.define('bi_pos_order_note.models', function(require){
	'use strict';

	var models = require('point_of_sale.models');
	var core = require('web.core');
	var field_utils = require('web.field_utils');
	var rpc = require('web.rpc');
	var session = require('web.session');
	var time = require('web.time');
	var utils = require('web.utils');
	var _t = core._t;

	var OrderlineSuper = models.Orderline.prototype;
	models.Orderline = models.Orderline.extend({
		initialize: function(attr,options){
			OrderlineSuper.initialize.apply(this, arguments);
			this.notes_product_line = this.notes_product_line || '';
		},

		clone: function(){
	        var res = OrderlineSuper.clone.call(this);
	        res.notes_product_line = this.notes_product_line;
	        return res;
	    },

		set_notes_product_line: function(notes_product_line){
		  this.notes_product_line = notes_product_line;
		  this.trigger('change',this);
		},

		get_notes_product_line: function(){
			return this.notes_product_line;
		},

		export_as_JSON: function(){
			var json = OrderlineSuper.export_as_JSON.call(this);
			json.notes_product_line = this.notes_product_line;
			return json;
		},
		init_from_JSON: function(json){
			OrderlineSuper.init_from_JSON.apply(this,arguments);
			this.notes_product_line = json.notes_product_line;
		},

		export_for_printing: function(){
			var json = OrderlineSuper.export_for_printing.call(this);
			json.notes_product_line = this.notes_product_line;
			return json;
		},
	
	});

});
