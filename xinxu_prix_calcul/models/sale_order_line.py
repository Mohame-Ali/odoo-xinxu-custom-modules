# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # ─────────────────────────────────────────────────────────────────────────
    # Fournisseur retenu + délai
    # ─────────────────────────────────────────────────────────────────────────

    x_supplier_id = fields.Many2one(
        comodel_name='res.partner',
        string='Fournisseur',
        domain=[('supplier_rank', '>=', 0)],
        help="Fournisseur retenu après le Tableau Comparatif.",
    )

    x_delivery_time = fields.Char(
        string='Délai de livraison',
        help="Délai indiqué par le fournisseur (ex : 2 Weeks, In Stock).",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Prix fournisseur (séparé de price_unit)
    # ─────────────────────────────────────────────────────────────────────────

    x_supplier_price = fields.Float(
        string='Prix fournisseur',
        digits=(16, 4),
        default=0.0,
        help="Prix d'achat fournisseur. "
             "Le prix de vente calculé sera écrit automatiquement "
             "dans le Prix Unitaire des Lignes de Commande.",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # CHAMPS COMMUNS — saisie manuelle
    # ─────────────────────────────────────────────────────────────────────────

    x_conversion_rate = fields.Float(
        string='Taux de conversion',
        digits=(16, 6),
        default=1.0,
        help="Taux de conversion vers la devise du devis.\n"
            "Exemples :\n"
            "- Devis en TND : saisir 3.20 pour convertir USD → TND\n"
            "- Devis en EUR : saisir 0.93 pour convertir USD → EUR\n"
            "À saisir manuellement (ne pas utiliser le taux automatique).",
    )

    x_margin_pct = fields.Float(
        string='Marge (%)',
        digits=(5, 4),
        default=0.10,
        help="Pourcentage de marge commerciale.\n"
             "LOCAL    : défaut 10 %  → saisir 0.10\n"
             "ÉTRANGER : défaut 13 %  → saisir 0.13",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # CHAMPS LOCAL — saisie manuelle
    # ─────────────────────────────────────────────────────────────────────────

    x_customs_duties_pct = fields.Float(
        string='Droits de douane (%)',
        digits=(5, 4),
        default=0.01,
        help="Droits de douane appliqués sur le prix fournisseur.\n"
             "Défaut : 1 %  → saisir 0.01",
    )

    x_fodec_pct = fields.Float(
        string='FODEC (%)',
        digits=(5, 4),
        default=0.01,
        help="Fonds de Développement de la Compétitivité.\n"
             "Défaut : 1 %  → saisir 0.01",
    )

    x_impot_douane_pct = fields.Float(
        string='Impôt douane (%)',
        digits=(5, 4),
        default=0.30,
        help="Impôt de douane tunisien.\n"
             "Défaut : 30 %  → saisir 0.30",
    )

    x_avance_import_pct = fields.Float(
        string='Avance sur Import (%)',
        digits=(5, 4),
        default=0.03,
        help="Avance sur impôt à l'importation.\n"
             "Défaut : 3 %  → saisir 0.03",
    )

    x_tva_pct = fields.Float(
        string='TVA (%)',
        digits=(5, 4),
        default=0.19,
        help="Taux de TVA tunisien.\n"
             "Défaut : 19 %  → saisir 0.19",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # CHAMPS CALCULÉS — TABLEAU LOCAL 
    # ─────────────────────────────────────────────────────────────────────────

    x_total_price_orig = fields.Float(
        string='Prix total (devise origine)',
        compute='_compute_local', store=True, digits=(16, 4),
        help="F = Prix fournisseur × (1 + Droits de douane %)",
    )
    x_price_tnd = fields.Float(
        string='Prix après conversion',
        compute='_compute_local', store=True, digits=(16, 4),
        help="I = Prix total devise × Taux de conversion ",
    )
    x_price_fodec = fields.Float(
        string='Prix + FODEC',
        compute='_compute_local', store=True, digits=(16, 4),
        help="K = Prix après conversion × (1 + FODEC %)",
    )
    x_price_all_taxes = fields.Float(
        string='Prix avec impôt douane',
        compute='_compute_local', store=True, digits=(16, 4),
        help="M = Prix+FODEC × (1 + Impôt douane %)",
    )
    x_total_cost_tnd = fields.Float(
        string='Coût total ',
        compute='_compute_local', store=True, digits=(16, 4),
        help="O = Prix toutes taxes × (1 + Avance sur Import %)",
    )
    x_prix_htva = fields.Float(
        string='Prix unitaire HTVA',
        compute='_compute_local', store=True, digits=(16, 4),
        help="Q = Coût total ÷ (1 − Marge %)",
    )
    x_marge_unitaire = fields.Float(
        string='Marge unitaire (local)',
        compute='_compute_local', store=True, digits=(16, 4),
        help="R = Prix HTVA − Coût total ",
    )
    x_montant_tva = fields.Float(
        string='Montant TVA',
        compute='_compute_local', store=True, digits=(16, 4),
        help="T = Prix HTVA × TVA %",
    )
    x_prix_ttc = fields.Float(
        string='Prix de vente TTC',
        compute='_compute_local', store=True, digits=(16, 4),
        help="U = Prix HTVA + Montant TVA → PRIX DE VENTE CLIENT",
    )
    x_prix_total_ttc = fields.Float(
        string='Prix total TTC',
        compute='_compute_local', store=True, digits=(16, 4),
        help="W = Prix TTC × Quantité",
    )
    x_marge_total_local = fields.Float(
        string='Marge totale (local)',
        compute='_compute_local', store=True, digits=(16, 4),
        help="X = Marge unitaire × Quantité",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # CHAMPS CALCULÉS — TABLEAU ÉTRANGER 
    # ─────────────────────────────────────────────────────────────────────────

    x_price_eur = fields.Float(
        string='Coût converti',
        compute='_compute_foreign', store=True, digits=(16, 4),
        help="Prix fournisseur converti dans la devise du devis.",
    )
    x_unit_sell_price_eur = fields.Float(
        string='Prix de vente unitaire (converti)',
        compute='_compute_foreign', store=True, digits=(16, 4),
        help="Prix de vente unitaire proposé au client (coût converti ÷ (1 − Marge %)).",
    )
    x_prix_total_eur = fields.Float(
        string='Prix de vente suggéré ',
        compute='_compute_foreign', store=True, digits=(16, 4),
        help="Montant total de la ligne = Quantité × Prix de vente suggéré.",
    )
    x_margin_value_eur = fields.Float(
        string='Marge unitaire (étranger) ',
        compute='_compute_foreign', store=True, digits=(16, 4),
        help="Marge par unité = Prix de vente suggéré − Coût converti.",
    )
    x_marge_total_eur = fields.Float(
        string='Marge totale (étranger)',
        compute='_compute_foreign', store=True, digits=(16, 4),
        help="Marge totale = Marge unitaire × Quantité.",
    )

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE — TABLEAU LOCAL
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends(
        'x_supplier_price',
        'product_uom_qty',
        'x_customs_duties_pct',
        'x_conversion_rate',
        'x_fodec_pct',
        'x_impot_douane_pct',
        'x_avance_import_pct',
        'x_margin_pct',
        'x_tva_pct',
        'order_id.xinxu_calc_type',
    )
    def _compute_local(self):
        for line in self:
            margin = min(line.x_margin_pct, 0.9999)

            f = line.x_supplier_price * (1.0 + line.x_customs_duties_pct)
            i = f * line.x_conversion_rate
            k = i * (1.0 + line.x_fodec_pct)
            m = k * (1.0 + line.x_impot_douane_pct)
            o = m * (1.0 + line.x_avance_import_pct)
            q = o / (1.0 - margin) if margin < 1.0 else 0.0
            r = q - o
            t = q * line.x_tva_pct
            u = q + t
            w = u * line.product_uom_qty
            x = r * line.product_uom_qty

            line.x_total_price_orig  = f
            line.x_price_tnd         = i
            line.x_price_fodec       = k
            line.x_price_all_taxes   = m
            line.x_total_cost_tnd    = o
            line.x_prix_htva         = q
            line.x_marge_unitaire    = r
            line.x_montant_tva       = t
            line.x_prix_ttc          = u
            line.x_prix_total_ttc    = w
            line.x_marge_total_local = x

            # Écrire le prix de vente TTC dans price_unit — DANS la boucle for
            if line.order_id.xinxu_calc_type == 'local':
                line.price_unit = u

    # ─────────────────────────────────────────────────────────────────────────
    # COMPUTE — TABLEAU ÉTRANGER
    # ─────────────────────────────────────────────────────────────────────────

    @api.depends(
        'x_supplier_price',
        'product_uom_qty',
        'x_conversion_rate',
        'x_margin_pct',
        'order_id.xinxu_calc_type',
    )
    def _compute_foreign(self):
        for line in self:
            margin = min(line.x_margin_pct, 0.9999)

            k = line.x_supplier_price * line.x_conversion_rate
            m = k / (1.0 - margin) if margin < 1.0 else 0.0
            n = line.product_uom_qty * m
            o = m - k
            p = o * line.product_uom_qty

            line.x_price_eur           = k
            line.x_unit_sell_price_eur = m
            line.x_prix_total_eur      = n
            line.x_margin_value_eur    = o
            line.x_marge_total_eur     = p

            # Écrire le prix de vente EUR dans price_unit — DANS la boucle for  
            if line.order_id.xinxu_calc_type == 'foreign':
                line.price_unit = m