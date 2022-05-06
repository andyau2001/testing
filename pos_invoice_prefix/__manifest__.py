# -*- coding: utf-8 -*-
{
	'name': 'Pos Invoice Prefix',
	'author': 'Youaddon',
	'version': '14.0.1.0',
	'live_test_url': ' ',
	'summary': 'Invoice Prefix In Pos',
	'description': """Invoice Prefix in Pos""",
	'license': "OPL-1",
	'depends': ['point_of_sale','account'],
	'data': [
			'views/pos_templates.xml'
			],
	'qweb': [
			'static/src/xml/payment_button.xml'
			],
	'installable': True,
	'auto_install': False,
	'category': 'Point of Sale',
}
