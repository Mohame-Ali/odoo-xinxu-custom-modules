# -*- coding: utf-8 -*-
from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    mission_count = fields.Integer(
        string='Nb missions',
        compute='_compute_mission_count',
        help="Nombre total d'ordres de mission (tous états confondus).",
    )

    def _compute_mission_count(self):
        counts = {
            employee.id: count
            for employee, count in self.env['mission.order'].sudo()._read_group(
                [('employee_id', 'in', self.ids)],
                groupby=['employee_id'],
                aggregates=['__count'],
            )
        }
        for employee in self:
            employee.mission_count = counts.get(employee.id, 0)

    def action_view_missions(self):
        """Smart-button action — open missions for this employee."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Missions — {self.name}',
            'res_model': 'mission.order',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }