# -*- coding: utf-8 -*-
"""
Extends res.company with the extra banking / contact fields shown on the
XINXU COMPANYY invoice header.

These fields are editable in:
  Settings → Companies → [your company] → (scroll down) XINXU Invoice Info
"""

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    xinxu_rib = fields.Char(
        string='RIB',
        help='Bank account number (RIB) displayed on the invoice header. '
             'Example: 04 305 056 0074613696 86',
    )
    xinxu_bank_name = fields.Char(
        string='Banque',
        help='Name of the company bank shown on the invoice header. '
             'Example: Attijari Banque',
    )
    xinxu_bank_agency = fields.Char(
        string='Agence bancaire',
        help='Bank branch / agency shown on the invoice header. '
             'Example: Bou Argoub',
    )
