# -*- coding: utf-8 -*-
{
    'name': "Material Requisitions",

    'summary': """
        ABK Material Requisitions""",

    'description': """
        ABK Material Requisitions
    """,

    'author': "AboutKnowledge",
    'website': "https://www.aboutknowledge.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'account', 'purchase'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/abk_material_requisitions_view.xml',
        'views/templates.xml',
        'views/abk_terms_conditions_view.xml',
        'views/res_config_settings_view.xml',
    ],
}
