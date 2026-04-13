from odoo import fields, models

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    mission_id = fields.Many2one('mission.order', string='Ordre de mission', ondelete='set null',
                                 domain="[('employee_id', '=', employee_id), ('state', '=', 'approved')]")