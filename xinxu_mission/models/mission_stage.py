from odoo import fields, models

class MissionStage(models.Model):
    _name = 'mission.stage'
    _description = 'Mission Stage'
    _order = 'departure_datetime'

    mission_id = fields.Many2one('mission.order', string='Mission', required=True, ondelete='cascade')
    destination = fields.Char(string='Lieu de Destination', required=True)
    departure_datetime = fields.Datetime(string='Date et Heure de DEPART', required=True)
    return_datetime = fields.Datetime(string='Date et Heure de RETOUR', required=True)
    departure_location = fields.Char(string="Lieu de départ", default='RA')   # RA / RF?
    return_location = fields.Char(string="Lieu de retour", default='RA')
    departure_ra = fields.Boolean(string="RA (départ)")
    departure_rf = fields.Boolean(string="RF (départ)")
    return_ra = fields.Boolean(string="RA (retour)")
    return_rf = fields.Boolean(string="RF (retour)")

    # Simple approach: we can just have two Char fields for departure/return locations.
    # For simplicity, we'll use text fields and let the user type "RA" or "RF".
    # Alternatively, we can have selection fields.
    # We'll keep it simple to match the paper.