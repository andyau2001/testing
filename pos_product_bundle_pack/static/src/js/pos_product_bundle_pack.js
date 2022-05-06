// pos_product_bundle_pack js
odoo.define('pos_product_bundle_pack.pos', function(require) {
    "use strict";

    var models = require('point_of_sale.models');
    var core = require('web.core');

    var _t = core._t;



    var _super_posmodel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            var product_model = _.find(this.models, function(model){ return model.model === 'product.product'; });
            product_model.fields.push('is_pack','cal_pack_price','pack_ids');            
            return _super_posmodel.initialize.call(this, session, attributes);
        },
    });


    models.load_models({
        model: 'product.pack',
        fields: ['product_id', 'qty_uom', 'bi_product_template', 'bi_image', 'price', 'uom_id', 'name'],
        domain: null,
        loaded: function(self, pos_product_pack) {
            self.pos_product_pack = pos_product_pack;
            self.set({
                'pos_product_pack': pos_product_pack
            });
        },
    });

    models.load_models({
        model: 'product.product',
        fields: ['is_pack','cal_pack_price','pack_ids','name'],
        domain: [['is_pack','=',true]],
        //domain: function(self){ return [['is_pack','=',true]]; },
        loaded: function(self, pos_product) {
            self.pos_product = pos_product;
            self.set({
                'pos_product': pos_product
            });
            //console.log("***************self.pos_productttttttttttttttttttttttt", self.pos_product);
        },
    });


// exports.Orderline = Backbone.Model.extend ...
    var OrderlineSuper = models.Orderline;
    models.Orderline = models.Orderline.extend({
		
		// initialize: function(attr,options){
  //           console.log(options,"------options")
		//     this.pos   = options.pos;
  //           console.log(this.pos,"------1")
		//     this.order = options.order;
  //           console.log(this.order,"------2")
		//     if (options.json) {
		//         this.init_from_JSON(options.json);
		//         return;
		//     }
		//     this.product = options.product;
  //           console.log(this.product,"------3")
		//     this.price   = options.product.price;
  //           console.log(this.price,"-----5")
		//     this.set_quantity(1);
		//     this.discount = 0;
		//     this.discountStr = '0';
		//     this.type = 'unit';
		//     this.selected = false;
		// },
		// init_from_JSON: function(json) {
		//     this.product = this.pos.db.get_product_by_id(json.product_id);
		//     if (!this.product) {
		//         console.error('ERROR: attempting to recover product not available in the point of sale');
		//     }
		//     this.price = json.price_unit;
  //           console.log(this.price,"-----4")
		//     this.set_discount(json.discount);
		//     this.set_quantity(json.qty);
		//     this.id    = json.id;
		// },

        export_for_printing: function(){
            return {
                quantity:           this.get_quantity(),
                unit_name:          this.get_unit().name,
                price:              this.get_unit_display_price(),
                discount:           this.get_discount(),
                product_name:       this.get_product().display_name,
                product_name_wrapped: this.generate_wrapped_product_name(),
                price_lst:          this.get_lst_price(),
                display_discount_policy:    this.display_discount_policy(),
                price_display_one:  this.get_display_price_one(),
                price_display :     this.get_display_price(),
                price_with_tax :    this.get_price_with_tax(),
                price_without_tax:  this.get_price_without_tax(),
                price_with_tax_before_discount:  this.get_price_with_tax_before_discount(),
                tax:                this.get_tax(),
                product_description:      this.get_product().description,
                product_description_sale: this.get_product().description_sale,
                get_product_bundle_pack : this.get_product_bundle_pack()
            };
        },
		
		// Pass Bundle Pack Products in Orderline WIdget.
        get_product_bundle_pack: function() {
            self = this;
            var pos_product_bundle_pack = [];
            var product =  this.get_product();
            var pos_products = self.pos.get('pos_product');
            var pos_product_packs = self.pos.get('pos_product_pack');
            for (var i = 0; i < pos_products.length; i++) {
                if (pos_products[i].id == product.id && (pos_products[i].pack_ids).length > 0) {
                    for (var j = 0; j < (pos_products[i].pack_ids).length; j++) {
                        for (var k = 0; k < pos_product_packs.length; k++) {
                            if (pos_product_packs[k].id == pos_products[i].pack_ids[j]) {
                                var product_items = {
                                    'display_name': pos_product_packs[k].name,
                                    'uom_id': pos_product_packs[k].uom_id,
                                    'price': pos_product_packs[k].price,
                                    'qty_uom': pos_product_packs[k].qty_uom
                                };
                                pos_product_bundle_pack.push({'product': product_items });
                            }
                        }
                    }
                    return pos_product_bundle_pack;
                }
            }
        },
    });
    



});
