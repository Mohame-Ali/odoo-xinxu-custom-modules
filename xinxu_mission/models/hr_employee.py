# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
        store=False,
        string='Devise',
    )

    # ── Relation to missions ─────────────────────────────────────────────────
    mission_ids = fields.One2many(
        comodel_name='mission.order',
        inverse_name='employee_id',
        string='Ordres de mission',
    )

    mission_count = fields.Integer(
        string='Nb missions',
        compute='_compute_mission_budget',
        store=True,
        help="Nombre total d'ordres de mission (tous états confondus).",
    )

    mission_approved_count = fields.Integer(
        string='Missions approuvées',
        compute='_compute_mission_budget',
        store=True,
        help="Nombre de missions en état 'Approuvé'.",
    )

    mission_total_approved_budget = fields.Monetary(
        string='Budget approuvé total',
        compute='_compute_mission_budget',
        store=True,
        currency_field='currency_id',
        help="Somme des budgets approuvés des missions en état 'Approuvé'.",
    )

    mission_total_spent = fields.Monetary(
        string='Total dépensé',
        compute='_compute_mission_budget',
        store=True,
        currency_field='currency_id',
        help="Somme des montants dépensés sur toutes les missions approuvées.",
    )

    mission_total_remaining = fields.Monetary(
        string='Reste budget',
        compute='_compute_mission_budget',
        store=True,
        currency_field='currency_id',
        help="Budget approuvé total − Total dépensé.",
    )


    @api.depends(
        'mission_ids',
        'mission_ids.state',
        'mission_ids.approved_budget',
        'mission_ids.spent_amount',
    )
    def _compute_mission_budget(self):
        for employee in self:
            all_missions = employee.mission_ids
            approved = all_missions.filtered(lambda m: m.state == 'approved')

            employee.mission_count = len(all_missions)
            employee.mission_approved_count = len(approved)
            employee.mission_total_approved_budget = sum(
                approved.mapped('approved_budget')
            )
            employee.mission_total_spent = sum(
                approved.mapped('spent_amount')
            )
            employee.mission_total_remaining = (
                employee.mission_total_approved_budget
                - employee.mission_total_spent
            )


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
