# -*- coding: utf-8 -*-
{
    'name': "ABK Xero Integration",

    'summary': """
        Xero Integration
        by Aboutknowledge""",

    'description': """
        Xero Integration by Aboutknowledge
    """,

    'author': "AboutKnowledge",
    'website': "https://www.aboutknowledge.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Productivity',
    'version': '14.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'account', 'product'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        "views/xero_tracking_category.xml",
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],

    'external_dependencies': {
        'python': ['xero-python', 'urllib3', 'dateutil']
    }
}
