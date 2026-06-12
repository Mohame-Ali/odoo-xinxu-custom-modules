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
        help="Bank account number (RIB) shown on document headers.",
    )
    xinxu_bank_name = fields.Char(
        string='Bank',
        help="Company bank name shown on document headers.",
    )
    xinxu_bank_agency = fields.Char(
        string='Bank Agency',
        help="Bank agency shown on document headers.",
    )
