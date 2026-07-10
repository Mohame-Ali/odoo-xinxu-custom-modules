# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # mission.order._compute_expense_totals reads this field on the expense
    # product to split the totals (Restauration / Transport / Frais divers).
    # It is accessible on product.product through the _inherits delegation.
    expense_category = fields.Selection(
        [
            ('restauration', 'Restauration'),
            ('transport', 'Transport'),
            ('divers', 'Frais divers'),
        ],
        string='Catégorie de frais mission',
        default='divers',
        help="Catégorie utilisée pour ventiler les dépenses liées aux ordres "
             "de mission (totaux Restauration / Transport / Frais divers).",
    )
