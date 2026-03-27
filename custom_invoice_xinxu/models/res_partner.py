from odoo import fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    x_ms_number = fields.Char(string='MS N.', help="Matricule statistique du client")