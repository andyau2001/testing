# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name" : "POS Order Notes in odoo",
    "version" : "14.0.1.0",
    "category" : "Point of Sale",
    "depends" : ['base','sale','point_of_sale'],
    "author": "BrowseInfo",
    'summary': 'Apps point of sales order note on pos order Receipt note on point of sale order note pos notes pos product notes order note POS Note POS Order line Notes POS line Note POS Receipt Note POS backend note Add notes POS order pos screen note on point of sale notes',
    "description": """
    
    Purpose :- 
    This Module allow us to add bag charges on particular order.
    POS order Note point of sales order note , point of sales note
	


    Add Note on POS

    POS Note

    POS Order line Note

    POS line Note

    POS Receipt Note

    POS backend NOte

    Add note on POS order

    Point Of Sale Note

    POS order Note

    Add Note on POS

    POS line Note

    Point of Sale Order line Note

    Point of Sale line Note

    Point of Sale Receipt Note

    Point of Sale backend NOte

    Add note on Point of Sale order
    """,
    "price": 9.89,

    "currency": 'EUR',
    "website" : "https://www.browseinfo.in",
    "data": [
        'views/bi_pos_order_note.xml',
    ],
    'qweb': [
        'static/src/xml/pos_order_note_template.xml',
    ],
    "auto_install": False,
    "installable": True,
    "live_test_url": "https://youtu.be/ZCq12gdW7Sg",
    "images":['static/description/Banner.png'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
