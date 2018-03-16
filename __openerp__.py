# -*- coding: utf-8 -*-
# Copyright 2017 Humanytek - Manuel Marquez <manuel@humanytek.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

{
    'name': 'Manager of returns not accepted in sale orders',
    'version': '9.0.1.2.0',
    'category': 'Sales',
    'summary': 'Manager of returns not accepted',
    'author': 'Humanytek',
    'website': "http://www.humanytek.com",
    'license': 'AGPL-3',
    'depends': ['stock', 'sale', 'stock_location_return_not_accepted', ],
    'data': [
        'views/sale_view.xml',
    ],
    'installable': True,
    'auto_install': False
}
