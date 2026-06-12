# -*- coding: utf-8 -*-
"""
Extends account.move (invoice) with per-invoice fields that appear in the
footer of the XINXU COMPANYY template.

These fields are editable directly on each invoice form (in the "Other Info"
tab or via a dedicated chatter widget — whichever you prefer).
"""

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    xinxu_delivery_mode = fields.Char(
        string='Delivery Mode',
        default='CPT ALGERIA',
        help="Delivery mode shown in the document footer.",
    )
    xinxu_origin_of_goods = fields.Char(
        string='Origin of Goods',
        default='TUNISIA',
        help="Country or region of origin shown in the document footer.",
    )
