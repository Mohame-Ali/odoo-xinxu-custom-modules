# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class MissionOrder(models.Model):
    _name = 'mission.order'
    _description = 'Mission Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    PROTECTED_MANAGER_FIELDS = {'manager_id', 'approval_date', 'approved_budget'}

    APPROVED_EDIT_WHITELIST = {
        'message_follower_ids', 'message_ids', 'activity_ids',
        'message_main_attachment_id',
    }

    ALLOWED_TRANSITIONS = {
        ('draft', 'submitted'): 'owner',
        ('refused', 'draft'): 'owner',
        ('submitted', 'approved'): 'manager',
        ('submitted', 'refused'): 'manager',
        ('approved', 'submitted'): 'manager', 
    }

    def _employee_id_domain(self):
        if self.env.user.has_group('xinxu_mission.group_mission_manager'):
            return []
        emps = self.env.user.employee_ids
        if emps:
            return [('id', 'in', emps.ids)]
        return [('id', '=', 0)]

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default='New')
    employee_id = fields.Many2one(
        'hr.employee.public',
        string='Nom, Prénom',
        required=True,
        tracking=True,
        default=lambda self: self.env.user.employee_id.id,
        domain=lambda self: self._employee_id_domain(),
    )
    function = fields.Char(string='Fonctions', help="Employee's function")
    personal_address = fields.Text(string='Résidence personnelle')
    accompanied_by = fields.Char(
        string='Accompagné de',
        help="Nom des personnes accompagnant l'employé lors de la mission, le cas échéant.",
    )
    particular_modalities = fields.Text(
        string='Modalités particulières',
        help="Conditions ou dispositions particulières applicables à cette mission "
            "(hébergement spécifique, contraintes horaires, etc.).",
    )

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

    estimated_costs = fields.Monetary(
        string='Coûts estimés',
        currency_field='currency_id',
        help="Montant estimé des dépenses de la mission, renseigné par l'employé avant validation.",
    )
    approved_budget = fields.Monetary(
        string='Budget approuvé',
        currency_field='currency_id',
        help="Budget validé par le responsable de mission chargé d'approuver la demande "
            "(et non par l'employé demandeur) ; sert de référence pour le suivi des "
            "dépenses réelles. Modifiable uniquement par ce responsable, et seulement "
            "tant que la mission est à l'état « Soumis ».",
    )
    spent_amount = fields.Monetary(
        string='Dépensé',
        compute='_compute_expense_totals',
        store=True,
        help="Somme des notes de frais validées (état Approuvé ou Payé) liées à cette mission. "
            "Calculé automatiquement.",
    )
    remaining_budget = fields.Monetary(
        string='Reste',
        compute='_compute_expense_totals',
        store=True,
        help="Différence entre le budget approuvé et le montant dépensé "
            "(Budget approuvé − Dépensé). Calculé automatiquement.",
    )
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    expense_ids = fields.One2many(
    'hr.expense', 'mission_id', string='Notes de frais',
    help="Notes de frais liées à cette mission. Une note de frais ne peut être rattachée "
         "qu'à une mission approuvée et doit appartenir au même employé.",
    )

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumis'),
        ('approved', 'Approuvé'),
        ('refused', 'Refusé'),
    ], default='draft', tracking=True, copy=False)

    manager_id = fields.Many2one('res.users', string='Responsable approbateur', readonly=True, copy=False)

    request_date = fields.Date(string='Date demande', default=fields.Date.today)
    approval_date = fields.Date(string="Date d'approbation", readonly=True, copy=False)

    is_mission_owner = fields.Boolean(
        string="Ordre de mission personnel",
        compute='_compute_user_flags',
        help="Vrai si l'employé de la mission est lié à l'utilisateur courant.",
    )
    is_mission_manager = fields.Boolean(
        string="Responsable de mission",
        compute='_compute_user_flags',
        help="Vrai si l'utilisateur courant appartient au groupe Responsable de mission.",
    )
    is_system_admin = fields.Boolean(
        string="Administrateur système",
        compute='_compute_user_flags',
        help="Vrai si l'utilisateur courant est administrateur système.",
    )

    total_restauration = fields.Monetary(string='Total Restauration', compute='_compute_expense_totals', store=True)
    total_transport = fields.Monetary(string='Total Transport', compute='_compute_expense_totals', store=True)
    total_divers = fields.Monetary(string='Total Frais divers', compute='_compute_expense_totals', store=True)
    total_expenses = fields.Monetary(string='Total', compute='_compute_expense_totals', store=True)

    # ------------------------------------------------------------------
    # Computes / constraints
    # ------------------------------------------------------------------

    @api.depends('employee_id')
    def _compute_user_flags(self):
        user = self.env.user
        is_manager = user.has_group('xinxu_mission.group_mission_manager')
        is_admin = self.env.su or user.has_group('base.group_system')
        user_emp_ids = user.employee_ids.ids
        for mission in self:
            mission.is_mission_manager = is_manager
            mission.is_system_admin = is_admin
            mission.is_mission_owner = bool(mission.employee_id) and mission.employee_id.id in user_emp_ids

    @api.depends(
        'expense_ids',
        'expense_ids.total_amount',
        'expense_ids.state',
        'expense_ids.product_id',
        'approved_budget',
    )
    def _compute_expense_totals(self):
        """Single compute for every expense-derived amount.

        An expense counts once it is validated: state 'approved' AND 'done'
        (paid). Counting only 'approved' would silently remove an expense
        from the totals the moment it gets paid.
        """
        counted_states = ('approved', 'done')
        for mission in self:
            restauration = transport = divers = 0.0
            for expense in mission.expense_ids.filtered(lambda e: e.state in counted_states):
                category = expense.product_id.expense_category
                if category == 'restauration':
                    restauration += expense.total_amount
                elif category == 'transport':
                    transport += expense.total_amount
                else:
                    divers += expense.total_amount
            mission.total_restauration = restauration
            mission.total_transport = transport
            mission.total_divers = divers
            mission.total_expenses = restauration + transport + divers
            mission.spent_amount = mission.total_expenses
            mission.remaining_budget = mission.approved_budget - mission.spent_amount

    @api.constrains('approved_budget')
    def _check_budget_positive(self):
        for mission in self:
            if mission.approved_budget < 0:
                raise ValidationError(_("Le budget approuvé ne peut être négatif."))

    # ------------------------------------------------------------------
    # Access helpers
    # ------------------------------------------------------------------

    def _is_system_admin(self):
        """The DG / system administrator account is allowed to act on its own missions."""
        return self.env.su or self.env.user.has_group('base.group_system')

    def _is_mission_manager(self):
        return self.env.user.has_group('xinxu_mission.group_mission_manager')

    def _check_mission_owner(self, mission, error_msg):
        """Ensure the current user owns this mission (its employee is linked to the user).

        Submitting and resetting to draft are OWNER-ONLY actions: managers are NOT
        exempt (only the superuser is, for technical/backend operations).
        """
        if self.env.su:
            return
        if not self.env.user.employee_ids:
            raise UserError(_(
                "Aucun employé RH n'est lié à votre utilisateur. "
                "Sur la fiche Employé, renseignez le champ « Utilisateur » avec ce compte, "
                "puis réessayez."
            ))
        if mission.employee_id.id not in self.env.user.employee_ids.ids:
            raise UserError(error_msg)

    def _check_mission_employee_for_user(self, employee_id):
        if self.env.su or self._is_mission_manager():
            return
        if not employee_id:
            return
        if employee_id not in self.env.user.employee_ids.ids:
            raise UserError(_(
                "Vous ne pouvez créer ou modifier un ordre de mission que pour votre fiche employé liée à ce compte. "
                "Dans Employés, ouvrez votre fiche et renseignez le champ « Utilisateur » avec cet utilisateur, "
                "puis enregistrez."
            ))

    def _validate_state_transition(self, mission, old_state, new_state):
        """Server-side enforcement of the approval workflow (form buttons are
        client-side only: any user with write access could otherwise set an
        arbitrary state through RPC, e.g. self-approve a mission)."""
        if old_state == new_state:
            return
        role = self.ALLOWED_TRANSITIONS.get((old_state, new_state))
        state_labels = dict(self._fields['state']._description_selection(self.env))
        if role is None:
            raise UserError(_(
                "Transition d'état non autorisée : « %(old)s » → « %(new)s » (%(mission)s).",
                old=state_labels.get(old_state, old_state),
                new=state_labels.get(new_state, new_state),
                mission=mission.name,
            ))
        if role == 'owner':
            self._check_mission_owner(mission, _(
                "Seul le demandeur de l'ordre de mission %s peut effectuer cette action.",
            ) % mission.name)
        else:  # 'manager'
            if not self._is_mission_manager() and not self._is_system_admin():
                raise UserError(_(
                    "Seul un responsable de mission peut approuver, refuser ou "
                    "annuler l'approbation d'un ordre de mission (%s).",
                ) % mission.name)
            if mission.employee_id.user_id == self.env.user and not self._is_system_admin():
                raise UserError(_(
                    "Vous ne pouvez pas approuver, refuser ou annuler l'approbation "
                    "de votre propre ordre de mission (%s).",
                ) % mission.name)

    # ------------------------------------------------------------------
    # Workflow actions
    # ------------------------------------------------------------------

    def action_submit(self):
        for mission in self:
            if mission.state != 'draft':
                raise UserError(_("Seul un ordre de mission en brouillon peut être soumis (%s).") % mission.name)
            self._check_mission_owner(mission, _(
                "Vous ne pouvez soumettre que vos propres ordres de mission. "
                "Choisissez votre employé dans « Nom, Prénom »."
            ))
        self.write({'state': 'submitted'})

    def action_approve(self):
        for mission in self:
            if mission.state != 'submitted':
                raise UserError(_("Seul un ordre de mission soumis peut être approuvé (%s).") % mission.name)
            if mission.employee_id.user_id == self.env.user and not self._is_system_admin():
                raise UserError(_("Vous ne pouvez pas approuver votre propre ordre de mission."))
            mission.write({
                'state': 'approved',
                'manager_id': self.env.user.id,
                'approval_date': fields.Date.today(),
                'approved_budget': mission.approved_budget or mission.estimated_costs or 0,
            })

    def action_refuse(self):
        for mission in self:
            if mission.state != 'submitted':
                raise UserError(_("Seul un ordre de mission soumis peut être refusé (%s).") % mission.name)
            if mission.employee_id.user_id == self.env.user and not self._is_system_admin():
                raise UserError(_("Vous ne pouvez pas refuser votre propre ordre de mission."))
        self.write({'state': 'refused'})

    def action_reset_to_draft(self):
        for mission in self:
            if mission.state != 'refused':
                raise UserError(_("Seul un ordre de mission refusé peut être remis en brouillon (%s).") % mission.name)
            self._check_mission_owner(mission, _(
                "Vous ne pouvez remettre en brouillon que vos propres ordres de mission."
            ))

        self.write({'state': 'draft'})

    def action_cancel_approval(self):
        for mission in self:
            if mission.state != 'approved':
                raise UserError(_("Seul un ordre de mission approuvé peut voir son approbation annulée (%s).") % mission.name)
            if mission.employee_id.user_id == self.env.user and not self._is_system_admin():
                raise UserError(_(
                    "Vous ne pouvez pas annuler l'approbation "
                    "de votre propre ordre de mission."
                ))

        for mission in self:
            mission_expenses = mission.expense_ids
            if mission_expenses:
                mission.message_post(
                    body=_(
                        "%(count)s note(s) de frais détachée(s) suite à "
                        "l'annulation de l'approbation.",
                        count=len(mission_expenses),
                    ),
                    subject=_("Notes de frais détachées"),
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                )
        expenses = self.mapped('expense_ids')
        if expenses:
            expenses.sudo().write({'mission_id': False})

        self.write({
            'state': 'submitted',
            'manager_id': False,
            'approval_date': False,
            'approved_budget': 0,
        })

    # ------------------------------------------------------------------
    # CRUD overrides
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        is_manager = self._is_mission_manager()
        is_admin = self._is_system_admin()
        for vals in vals_list:
            if vals.get('employee_id'):
                self._check_mission_employee_for_user(vals['employee_id'])
            if not self.env.su and not is_manager and not is_admin:
                if vals.get('state') and vals['state'] != 'draft':
                    raise UserError(_("Un nouvel ordre de mission doit être créé à l'état brouillon."))
                touched = set(vals) & self.PROTECTED_MANAGER_FIELDS
                if touched:
                    raise UserError(_(
                        "Les champs d'approbation (%s) sont réservés aux responsables de mission.",
                    ) % ', '.join(sorted(touched)))
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('mission.order') or 'New'
            if not vals.get('function') and vals.get('employee_id'):

                employee = self.env['hr.employee.public'].browse(vals['employee_id'])
                vals['function'] = employee.job_title or ''
        records = super().create(vals_list)
        for record in records:
            if record.employee_id and record.employee_id.user_id:
                record.message_subscribe(partner_ids=[record.employee_id.user_id.partner_id.id])
        return records

    def write(self, vals):
        if vals.get('employee_id'):
            self._check_mission_employee_for_user(vals['employee_id'])

        old_states = {mission.id: mission.state for mission in self}

        if not self.env.su:
            is_manager = self._is_mission_manager()
            is_admin = self._is_system_admin()

            if not is_manager and not is_admin:
                touched = set(vals) & self.PROTECTED_MANAGER_FIELDS
                if touched:
                    raise UserError(_(
                        "Les champs d'approbation (%s) sont réservés aux responsables de mission.",
                    ) % ', '.join(sorted(touched)))

                meaningful = set(vals) - self.APPROVED_EDIT_WHITELIST
                if meaningful:
                    frozen = self.filtered(lambda m: m.state == 'approved')
                    if frozen:
                        raise UserError(_(
                            "Un ordre de mission approuvé ne peut plus être modifié (%s). "
                            "Demandez à un responsable d'annuler l'approbation.",
                        ) % ', '.join(frozen.mapped('name')))

            if 'state' in vals:
                for mission in self:
                    self._validate_state_transition(mission, old_states[mission.id], vals['state'])

        res = super().write(vals)

        if vals.get('state') == 'draft':
            to_clear = self.filtered(lambda m: m.manager_id or m.approval_date)
            if to_clear:
                to_clear.sudo().write({'manager_id': False, 'approval_date': False})

        if 'state' in vals:
            self._notify_state_change(old_states)
        return res

    def unlink(self):
        if not self.env.su and not self._is_mission_manager() and not self._is_system_admin():
            blocked = self.filtered(lambda m: m.state not in ('draft', 'refused'))
            if blocked:
                raise UserError(_(
                    "Seuls les ordres de mission en brouillon ou refusés peuvent être "
                    "supprimés (%s). Un ordre soumis ou approuvé fait partie de "
                    "l'historique d'approbation.",
                ) % ', '.join(blocked.mapped('name')))
        return super().unlink()

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    def _notify_state_change(self, old_states):
        """Post chatter notifications after a state change.

        Uses the per-record old state captured before write() so that batch
        operations notify each mission correctly.
        """
        for mission in self:
            old_state = old_states.get(mission.id)
            new_state = mission.state
            if old_state == new_state:
                continue
            if new_state == 'submitted':
                manager_partners = self.env.ref('xinxu_mission.group_mission_manager').users.partner_id
                if manager_partners:
                    mission.message_subscribe(partner_ids=manager_partners.ids)
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
