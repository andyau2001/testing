# -*- coding: utf-8 -*-
{
    'name': "abk_hr_expense",

    'summary': """ABK Custom HR Expense""",

    'description': """
        ABK Custom HR Expense
    """,

    'author': "ABK",
    'website': "https://www.aboutknowledge.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Human Resources',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr_expense', 'sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
