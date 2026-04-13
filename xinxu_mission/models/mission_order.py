from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class MissionOrder(models.Model):
    _name = 'mission.order'
    _description = 'Mission Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    def _employee_id_domain(self):
        """Managers: full list (subject to hr.employee.public rules). Mission users with a linked
        HR card: only those employees. If none linked yet, no extra domain so the public directory
        is searchable (same visibility as elsewhere in Odoo); mission record rules still apply.
        """
        if self.env.user.has_group('xinxu_mission.group_mission_manager'):
            return []
        emps = self.env.user.employee_ids
        if emps:
            return [('id', 'in', emps.ids)]
        return []

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    employee_id = fields.Many2one(
        'hr.employee.public',
        string='Nom, Prénom',
        required=True,
        tracking=True,
        default=lambda self: self.env.user.employee_id,
        domain=lambda self: self._employee_id_domain(),
    )
    function = fields.Char(string='Fonctions', help="Employee's function")
    personal_address = fields.Text(string='Résidence personnelle')
    accompanied_by = fields.Char(string='Accompagné de')
    particular_modalities = fields.Text(string='Modalités particulières')

    stage_ids = fields.One2many('mission.stage', 'mission_id', string='Destinations')

    purpose = fields.Text(string='Motif du déplacement', required=True, tracking=True)

    transport_mode = fields.Selection([
        ('vehicle_service', 'Véhicule de service'),
        ('personal_vehicle', 'Véhicule personnel'),
        ('public_transport', 'Titres de transport'),
        ('actual_expenses', 'Frais réels'),
    ], string='Moyen de transport', required=True, default='public_transport')

    vehicle_brand = fields.Char(string='Marque')
    vehicle_plate = fields.Char(string="N° Immatriculation")
    personal_vehicle_reimbursement = fields.Selection([
        ('km_allowance', 'Indemnités kilométriques'),
        ('public_transport_rate', 'Tarif transport public le moins onéreux'),
    ], string='Remboursement véhicule personnel')

    estimated_costs = fields.Monetary(string='Coûts estimés', currency_field='currency_id')
    approved_budget = fields.Monetary(string='Budget approuvé', currency_field='currency_id')
    spent_amount = fields.Monetary(string='Dépensé', compute='_compute_spent_amount', store=True)
    remaining_budget = fields.Monetary(string='Reste', compute='_compute_spent_amount', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    expense_ids = fields.One2many('hr.expense', 'mission_id', string='Notes de frais')

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumis'),
        ('approved', 'Approuvé'),
        ('refused', 'Refusé'),
    ], default='draft', tracking=True, copy=False)

    manager_id = fields.Many2one('res.users', string='Responsable approbateur', readonly=True)

    request_date = fields.Date(string='Date demande', default=fields.Date.today)
    approval_date = fields.Date(string="Date d'approbation", readonly=True)

    total_restauration = fields.Monetary(string='Total Restauration', compute='_compute_expense_totals', store=True)
    total_transport = fields.Monetary(string='Total Transport', compute='_compute_expense_totals', store=True)
    total_divers = fields.Monetary(string='Total Frais divers', compute='_compute_expense_totals', store=True)
    total_expenses = fields.Monetary(string='Total', compute='_compute_expense_totals', store=True)

    @api.depends('expense_ids', 'expense_ids.total_amount', 'expense_ids.product_id')
    def _compute_expense_totals(self):
        for mission in self:
            restauration = transport = divers = 0
            for expense in mission.expense_ids.filtered(lambda e: e.state == 'approved'):
                if expense.product_id.expense_category == 'restauration':
                    restauration += expense.total_amount
                elif expense.product_id.expense_category == 'transport':
                    transport += expense.total_amount
                else:
                    divers += expense.total_amount
            mission.total_restauration = restauration
            mission.total_transport = transport
            mission.total_divers = divers
            mission.total_expenses = restauration + transport + divers

    @api.depends('expense_ids', 'expense_ids.total_amount', 'expense_ids.state')
    def _compute_spent_amount(self):
        for mission in self:
            approved_expenses = mission.expense_ids.filtered(lambda e: e.state == 'approved')
            mission.spent_amount = sum(approved_expenses.mapped('total_amount'))
            mission.remaining_budget = mission.approved_budget - mission.spent_amount

    @api.constrains('approved_budget')
    def _check_budget_positive(self):
        for mission in self:
            if mission.approved_budget < 0:
                raise ValidationError(_("Le budget approuvé ne peut être négatif."))

    def action_submit(self):
        for mission in self:
            if not self.env.user.has_group('xinxu_mission.group_mission_manager'):
                if not self.env.user.employee_ids:
                    raise UserError(_(
                        "Aucun employé RH n'est lié à votre utilisateur. "
                        "Sur la fiche Employé, renseignez le champ « Utilisateur » avec ce compte, "
                        "puis réessayez."
                    ))
                if mission.employee_id.id not in self.env.user.employee_ids.ids:
                    raise UserError(_(
                        "Le salarié sélectionné ne correspond pas à votre compte. "
                        "Choisissez votre employé dans « Nom, Prénom » (ou demandez un administrateur si le champ est vide)."
                    ))
        self.write({'state': 'submitted'})

    def action_approve(self):
        for mission in self:
            if mission.employee_id.user_id == self.env.user:
                raise UserError(_("Vous ne pouvez pas approuver votre propre ordre de mission."))
        self.write({
            'state': 'approved',
            'manager_id': self.env.user.id,
            'approval_date': fields.Date.today(),
            'approved_budget': self.approved_budget or self.estimated_costs or 0,
        })

    def action_refuse(self):
        for mission in self:
            if mission.employee_id.user_id == self.env.user:
                raise UserError(_("Vous ne pouvez pas refuser votre propre ordre de mission."))
        self.write({'state': 'refused'})

    def action_reset_to_draft(self):
        self.write({'state': 'draft', 'manager_id': False, 'approval_date': False})

    def _check_mission_employee_for_user(self, employee_id):
        """Mission users may only link orders to their own HR employee(s)."""
        if self.env.su or self.env.user.has_group('xinxu_mission.group_mission_manager'):
            return
        if not employee_id:
            return
        if employee_id not in self.env.user.employee_ids.ids:
            raise UserError(_(
                "Vous ne pouvez créer ou modifier un ordre de mission que pour votre fiche employé liée à ce compte. "
                "Dans Employés, ouvrez votre fiche et renseignez le champ « Utilisateur » avec cet utilisateur, "
                "puis enregistrez."
            ))

    def write(self, vals):
        if 'state' in vals:
            old_state = self.state
            new_state = vals['state']
            res = super().write(vals) 

            for mission in self:
                if old_state != new_state:
                    if new_state == 'submitted':
                        manager_user = self.env.ref('xinxu_mission.group_mission_manager').users[:1]
                        if manager_user:
                            mission.message_subscribe(partner_ids=[manager_user.partner_id.id])
                        mission.message_post(
                            body=_("Mission '%s' has been submitted by %s.") % (mission.name, mission.employee_id.name),
                            subject=_("Mission Submitted"),
                            message_type='notification',
                            subtype_xmlid='mail.mt_comment',
                        )
                    elif new_state == 'approved':
                        if mission.employee_id.user_id:
                            mission.message_post(
                                body=_("Mission '%s' has been approved by %s.") % (mission.name, self.env.user.name),
                                subject=_("Mission Approved"),
                                message_type='notification',
                                subtype_xmlid='mail.mt_comment',
                                partner_ids=[mission.employee_id.user_id.partner_id.id],
                            )
                    elif new_state == 'refused':
                        if mission.employee_id.user_id:
                            mission.message_post(
                                body=_("Mission '%s' has been refused by %s.") % (mission.name, self.env.user.name),
                                subject=_("Mission Refused"),
                                message_type='notification',
                                subtype_xmlid='mail.mt_comment',
                                partner_ids=[mission.employee_id.user_id.partner_id.id],
                            )
            return res
        else:
            if vals.get('employee_id'):
                self._check_mission_employee_for_user(vals['employee_id'])
            return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('employee_id'):
                self._check_mission_employee_for_user(vals['employee_id'])
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('mission.order') or 'New'
            if not vals.get('function') and vals.get('employee_id'):
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                vals['function'] = employee.job_title or ''
            employee = self.env['hr.employee'].browse(vals.get('employee_id'))
            if employee and employee.user_id:
                pass  
        records = super().create(vals_list)
        for record in records:
            if record.employee_id and record.employee_id.user_id:
                record.message_subscribe(partner_ids=[record.employee_id.user_id.partner_id.id])
        return records