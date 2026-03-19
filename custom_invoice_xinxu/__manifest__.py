# -*- coding: utf-8 -*-
{
    'name': 'Custom Invoice - XINXU Template',
    'version': '18.0.1.0.0',
    'summary': 'Personalised invoice report matching the XINXU COMPANYY layout',
    'description': """
        Overrides the standard Odoo 18 invoice PDF report with a custom QWeb template
        that matches the XINXU COMPANYY invoice design:
        - Full company header block (MF, RIB, Banque, Agence, Tel, Email)
        - Bordered invoice number + date header
        - Client info block (Client, Code client, Adresse, Téléphone)
        - Items table (Item Reference, Description, Qty, Unit price €, Total price €)
        - CPT total row
        - Footer block (Total says, Delivery mode, Payment terms, Origin of goods)
    """,
    'author': 'XINXU COMPANYY',
    'website': '',
    'category': 'Accounting/Accounting',
    'depends': ['account', 'stock', 'sale'],
    'data': [
        #'views/report_invoice.xml',
        'views/report_deliveryslip.xml',
        'views/report_proforma_local.xml',
        'views/report_proforma_foreign.xml',
        'views/res_company_view.xml',
        'views/report_xinxu_purchase_supplier.xml',
        'views/report_xinxu_facture_foreign.xml',
    ],
    'assets': {
        'web.report_assets_common': [
            'custom_invoice_xinxu/static/src/scss/invoice_xinxu.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
