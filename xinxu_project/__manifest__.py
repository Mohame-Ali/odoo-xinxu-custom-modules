# -*- coding: utf-8 -*-
{
    'name': 'XINXU Projects',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Project entity for linking sale orders to commercial projects.',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/xinxu_project_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
