# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    xinxu_project_id = fields.Many2one(
        'xinxu.project',
        string='XINXU Project',
        tracking=True,
        help='Link this quotation/order to a XINXU commercial project.',
    )
