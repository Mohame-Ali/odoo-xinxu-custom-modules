from odoo import api, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            picking_type_id = vals.get('picking_type_id')
            if picking_type_id:
                picking_type = self.env['stock.picking.type'].browse(picking_type_id)
                if picking_type.custom_sequence_id:
                    # Génère le prochain numéro selon la séquence configurée
                    vals['name'] = picking_type.custom_sequence_id.next_by_id()
        return super().create(vals_list)