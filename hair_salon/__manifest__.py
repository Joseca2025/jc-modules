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
    'version': '18.0.0.4',
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base','calendar','resource_booking','sale','sale_management','hr'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/hair_appointment_view.xml',
        'views/menu_hair_salon.xml',
        'views/resource_booking.xml',
        'views/calendar_event.xml',
    ],
}

