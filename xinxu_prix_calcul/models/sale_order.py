# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ─────────────────────────────────────────────────────────────────────────
    # Champ : type de tableau de calcul
    # ─────────────────────────────────────────────────────────────────────────

    xinxu_calc_type = fields.Selection(
        selection=[
            ('local',   'Client Local (TND)'),
            ('foreign', 'Client Étranger (EUR)'),
        ],
        string='Type de calcul',
        default='local',
        required=True,
        help="Détermine le tableau de calcul utilisé sur les lignes :\n"
             "• Local    → chaîne douanière TND (6 étapes)\n"
             "• Étranger → conversion EUR + marge (2 étapes)",
    )

    # Lien vers le(s) BC fournisseur(s) créé(s) depuis ce devis
    xinxu_purchase_ids = fields.Many2many(
        comodel_name='purchase.order',
        relation='xinxu_sale_purchase_rel',
        column1='sale_id',
        column2='purchase_id',
        string='Bons de commande fournisseur',
        copy=False,
    )

    xinxu_purchase_count = fields.Integer(
        compute='_compute_xinxu_purchase_count',
        string='Nbre BC fournisseur',
    )

    @api.depends('xinxu_purchase_ids')
    def _compute_xinxu_purchase_count(self):
        for order in self:
            order.xinxu_purchase_count = len(order.xinxu_purchase_ids)

    # ─────────────────────────────────────────────────────────────────────────
    # Bouton : créer le BC fournisseur depuis la commande de vente confirmée
    # ─────────────────────────────────────────────────────────────────────────

    def action_xinxu_create_purchase_order(self):
        """
        Crée un purchase.order depuis la commande de vente confirmée.

        Règles :
        - Toutes les lignes doivent avoir un fournisseur renseigné
          (x_supplier_id).
        - Un seul BC est créé par fournisseur (lignes regroupées).
        - Prix unitaire du BC = prix fournisseur saisi dans le
          Tableau de Calcul (price_unit de la ligne de vente, qui
          représente le prix fournisseur avant calcul de marge).
        - Le BC est créé en brouillon pour permettre une vérification
          avant envoi.
        """
        self.ensure_one()

        if self.state not in ('sale', 'done'):
            raise UserError(
                "Le bon de commande fournisseur ne peut être créé "
                "qu'après confirmation du devis par le client."
            )

        lines_with_supplier = self.order_line.filtered(
            lambda l: l.x_supplier_id and not l.display_type
        )

        if not lines_with_supplier:
            raise UserError(
                "Aucune ligne ne possède de fournisseur renseigné.\n"
                "Veuillez renseigner le champ 'Fournisseur' sur chaque "
                "ligne dans l'onglet Tableau de Calcul."
            )

        # Regrouper les lignes par fournisseur
        suppliers = lines_with_supplier.mapped('x_supplier_id')
        created_pos = self.env['purchase.order']

        for supplier in suppliers:
            supplier_lines = lines_with_supplier.filtered(
                lambda l: l.x_supplier_id == supplier
            )

            po_lines = []
            for sl in supplier_lines:
                po_lines.append((0, 0, {
                    'product_id':      sl.product_id.id,
                    'name':            sl.name,
                    'product_qty':     sl.product_uom_qty,
                    'product_uom':     sl.product_uom.id,
                    # Prix fournisseur = price_unit de la ligne de vente
                    # (c'est le prix achat saisi dans le Tableau de Calcul)
                    'price_unit':      sl.price_unit,
                    'date_planned':    fields.Datetime.now(),
                }))

            po = self.env['purchase.order'].create({
                'partner_id':  supplier.id,
                'origin':      self.name,
                'order_line':  po_lines,
                'notes':       _(
                    "Bon de commande créé automatiquement depuis le devis %s"
                ) % self.name,
            })
            created_pos |= po

        # Lier les BC créés à ce devis
        self.xinxu_purchase_ids |= created_pos

        # Ouvrir la liste des BC créés
        if len(created_pos) == 1:
            return {
                'type':      'ir.actions.act_window',
                'res_model': 'purchase.order',
                'res_id':    created_pos.id,
                'view_mode': 'form',
                'target':    'current',
            }
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain':    [('id', 'in', created_pos.ids)],
            'target':    'current',
        }

    def action_view_xinxu_purchases(self):
        """Bouton smart : voir les BC fournisseurs liés."""
        self.ensure_one()
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain':    [('id', 'in', self.xinxu_purchase_ids.ids)],
            'target':    'current',
        }
