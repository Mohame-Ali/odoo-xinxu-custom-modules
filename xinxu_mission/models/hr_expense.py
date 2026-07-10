# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    mission_id = fields.Many2one(
        'mission.order',
        string='Ordre de mission',
        ondelete='set null',
        index=True,
        domain="[('employee_id', '=', employee_id), ('state', '=', 'approved')]",
    )

    @api.constrains('mission_id', 'employee_id')
    def _check_mission_link(self):
        for expense in self:
            mission = expense.mission_id.sudo()
            if not mission:
                continue
            if expense.employee_id.id != mission.employee_id.id:
                raise ValidationError(_(
                    "La note de frais « %(expense)s » ne peut être liée qu'à un "
                    "ordre de mission de son propre employé (mission %(mission)s).",
                    expense=expense.name,
                    mission=mission.name,
                ))
            if mission.state != 'approved':
                raise ValidationError(_(
                    "Une note de frais ne peut être liée qu'à un ordre de mission "
                    "approuvé (mission %s).",
                ) % mission.name)