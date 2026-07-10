# -*- coding: utf-8 -*-
import operator as py_operator

from odoo import api, fields, models

OPERATORS = {
    '<': py_operator.lt,
    '<=': py_operator.le,
    '=': py_operator.eq,
    '!=': py_operator.ne,
    '>': py_operator.gt,
    '>=': py_operator.ge,
}


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    # hr.employee.public is the employee model readable by EVERY internal
    # user in Odoo 18 (hr.employee requires the HR Officer group). The
    # budget feature must therefore live here, otherwise the "Mon Budget
    # Mission" menu crashes with an AccessError for regular employees.

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
        store=False,
        string='Devise',
    )

    # Clean relation: mission.order.employee_id targets hr.employee.public,
    # so this One2many has a valid inverse on the same comodel.
    mission_ids = fields.One2many(
        comodel_name='mission.order',
        inverse_name='employee_id',
        string='Ordres de mission',
    )

    mission_count = fields.Integer(
        string='Nb missions',
        compute='_compute_mission_stats',
        help="Nombre total d'ordres de mission (tous états confondus).",
    )
    mission_approved_count = fields.Integer(
        string='Missions approuvées',
        compute='_compute_mission_stats',
        help="Nombre de missions en état 'Approuvé'.",
    )
    mission_total_approved_budget = fields.Monetary(
        string='Budget approuvé total',
        compute='_compute_mission_stats',
        currency_field='currency_id',
        help="Somme des budgets approuvés des missions en état 'Approuvé'.",
    )
    mission_total_spent = fields.Monetary(
        string='Total dépensé',
        compute='_compute_mission_stats',
        currency_field='currency_id',
        help="Somme des montants dépensés sur toutes les missions approuvées.",
    )
    mission_total_remaining = fields.Monetary(
        string='Reste budget',
        compute='_compute_mission_stats',
        search='_search_mission_total_remaining',
        currency_field='currency_id',
        help="Budget approuvé total − Total dépensé.",
    )
    mission_budget_usage = fields.Float(
        string='Utilisation du budget (%)',
        compute='_compute_mission_stats',
        help="Part du budget approuvé déjà dépensée, en pourcentage.",
    )

    def _compute_mission_stats(self):
        # Non-stored on purpose: the statistics are read through mission_ids
        # in the CURRENT user's environment, so record rules apply naturally
        # (an employee only aggregates their own missions, a manager sees
        # everyone's) and no stale stored value can leak across users.
        for employee in self:
            missions = employee.mission_ids
            approved = missions.filtered(lambda m: m.state == 'approved')
            total_budget = sum(approved.mapped('approved_budget'))
            total_spent = sum(approved.mapped('spent_amount'))
            employee.mission_count = len(missions)
            employee.mission_approved_count = len(approved)
            employee.mission_total_approved_budget = total_budget
            employee.mission_total_spent = total_spent
            employee.mission_total_remaining = total_budget - total_spent
            employee.mission_budget_usage = (total_spent / total_budget * 100.0) if total_budget else 0.0

    def _search_mission_total_remaining(self, operator, value):
        """Search support for the non-stored remaining-budget field
        ("Budget dépassé" / "Budget épuisé" filters).

        Employees without any approved mission have no budget and are
        treated as non-matching. The aggregation runs in the current user's
        environment, so record rules keep the result consistent with what
        the user can actually see.
        """
        if operator not in OPERATORS:
            return NotImplemented
        compare = OPERATORS[operator]
        groups = self.env['mission.order']._read_group(
            [('state', '=', 'approved')],
            groupby=['employee_id'],
            aggregates=['approved_budget:sum', 'spent_amount:sum'],
        )
        matching_ids = [
            employee.id
            for employee, budget, spent in groups
            if employee and compare((budget or 0.0) - (spent or 0.0), value)
        ]
        return [('id', 'in', matching_ids)]
