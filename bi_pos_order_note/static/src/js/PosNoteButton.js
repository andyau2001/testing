odoo.define('bi_pos_order_note.PosNoteButton', function(require){
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const ProductScreen = require('point_of_sale.ProductScreen');
	const { useListener } = require('web.custom_hooks');
	const Registries = require('point_of_sale.Registries');

	class PosNoteButton extends PosComponent {
		constructor() {
			super(...arguments);
			useListener('click', this.onClick);
		}

		get selectedOrderline() {
			return this.env.pos.get_order().get_selected_orderline();
		}

		async onClick() {
			let self = this;
			let order = self.env.pos.get_order();
			let orderlines = order.orderlines;
			if (orderlines.length === 0) {
				self.showPopup('ErrorPopup', {
					title: self.env._t('Empty Order'),
					body: self.env._t('There must be at least one product in your order before Add a note.'),
				});
				return;
			}
			else{
				
				const { confirmed, payload: inputNote } = await this.showPopup('TextAreaPopup', {
					startingValue: this.selectedOrderline.get_notes_product_line(),
					title: this.env._t('Add Note'),
				});

				if (confirmed) {
					this.selectedOrderline.set_notes_product_line(inputNote);
				}
			}
		}
	}
	PosNoteButton.template = 'PosNoteButton';

	ProductScreen.addControlButton({
		component: PosNoteButton,
		condition: function() {
			return true;
		},
	});

	Registries.Component.add(PosNoteButton);
	return PosNoteButton;

});
			