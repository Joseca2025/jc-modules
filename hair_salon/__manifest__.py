# -*- coding: utf-8 -*-
{
    'name': "hair_salon",

    'summary': "Module for Odoo 18 for hair salon management.",

    'description': """
        This module was developed for managing a hair salon, handling appointment scheduling, sales, service types, etc.
    """,

    'author': "Jose Carlos Alarcon",
    'website': "https://www.josecarlosalarcon.com",


    'category': 'Services',
    'version': '18.0.0.2',

    # any module necessary for this one to work correctly
    'depends': ['base','calendar','resource_booking','sale','sale_management','hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/hair_appointment_view.xml',
        'views/menu_hair_salon.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

