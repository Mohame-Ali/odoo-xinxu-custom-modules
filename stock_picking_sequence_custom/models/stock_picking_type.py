from odoo import fields, models

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    custom_sequence_id = fields.Many2one(
        'ir.sequence',
        string='Séquence personnalisée',
        help="Séquence utilisée pour générer le numéro des bons de livraison de ce type."
    )