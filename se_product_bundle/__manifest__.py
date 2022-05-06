# -*- coding: utf-8 -*-

{
    'name': 'Product Bundle Pack',
    'category': 'Sales',
    'version': '14.0',
    'author': 'SprintERP',
    'website': 'http://www.sprinterp.com',
    'summary': """Product Bundle Pack""",
    'description': """
        This plugin use for create Product Bundle Pack including multiple products, Discount etc.
    """,
    'depends': ['sale','product','stock','sale_stock','sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_view.xml',
        'views/product_bundle_view.xml',
        'wizard/product_bundle_view.xml',
        'views/sale_order_view.xml',
    ],
    'license': 'LGPL-3',
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': True,
    'price': 25,
    "currency": 'USD',
}
