# -*- coding: utf-8 -*-
from odoo import fields, models


class XinxuProject(models.Model):
    _name = 'xinxu.project'
    _description = 'XINXU Commercial Project'
    _order = 'year desc, name'

    name = fields.Char(string='Project Name', required=True)
    year = fields.Integer(string='Year', required=True)
    partner_id = fields.Many2one('res.partner', string='Client')
    user_id = fields.Many2one('res.users', string='Responsible')
    status = fields.Selection([
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='active', required=True)
    notes = fields.Text(string='Notes')

    sale_order_ids = fields.One2many('sale.order', 'xinxu_project_id', string='Quotations / Orders')

    order_count = fields.Integer(string='Orders', compute='_compute_order_count')
    total_revenue = fields.Monetary(string='Total Revenue', compute='_compute_total_revenue',
                                    currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    def _compute_order_count(self):
        for rec in self:
            rec.order_count = len(rec.sale_order_ids.filtered(
                lambda o: o.state in ('sale', 'done')
            ))

    def _compute_total_revenue(self):
        today = fields.Date.today()
        company = self.env.company
        company_currency = company.currency_id
        for rec in self:
            total = 0.0
            for order in rec.sale_order_ids.filtered(lambda o: o.state in ('sale', 'done')):
                total += order.currency_id._convert(
                    order.amount_total, company_currency, company, today
                )
            rec.total_revenue = total

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Orders — {self.name}',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('xinxu_project_id', '=', self.id)],
            'context': {'default_xinxu_project_id': self.id},
        }
