# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class MissionStage(models.Model):
    _name = 'mission.stage'
    _description = 'Mission Stage'
    _order = 'departure_datetime'

    mission_id = fields.Many2one('mission.order', string='Mission', required=True, ondelete='cascade', index=True)
    destination = fields.Char(string='Lieu de Destination', required=True)
    departure_datetime = fields.Datetime(string='Date et Heure de DEPART', required=True)
    return_datetime = fields.Datetime(string='Date et Heure de RETOUR', required=True)
    departure_location = fields.Char(string="Lieu de départ")
    return_location = fields.Char(string="Lieu de retour")

    @api.constrains('departure_datetime', 'return_datetime')
    def _check_dates(self):
        for stage in self:
            if (stage.departure_datetime and stage.return_datetime
                    and stage.return_datetime <= stage.departure_datetime):
                raise ValidationError(_(
                    "La date de retour doit être postérieure à la date de départ "
                    "(destination : %s).",
                ) % (stage.destination or ''))

    def _check_mission_editable(self, missions):
        if self.env.su or self.env.user.has_group('xinxu_mission.group_mission_manager') \
                or self.env.user.has_group('base.group_system'):
            return
        frozen = missions.filtered(lambda m: m.state == 'approved')
        if frozen:
            raise UserError(_(
                "Les destinations d'un ordre de mission approuvé ne peuvent plus "
                "être modifiées (%s).",
            ) % ', '.join(frozen.mapped('name')))

    @api.model_create_multi
    def create(self, vals_list):
        mission_ids = [vals['mission_id'] for vals in vals_list if vals.get('mission_id')]
        if mission_ids:
            self._check_mission_editable(self.env['mission.order'].browse(mission_ids))
        return super().create(vals_list)

    def write(self, vals):
        missions = self.mapped('mission_id')
        if vals.get('mission_id'):
            missions |= self.env['mission.order'].browse(vals['mission_id'])
        self._check_mission_editable(missions)
        return super().write(vals)

    def unlink(self):
        self._check_mission_editable(self.mapped('mission_id'))
        return super().unlink()