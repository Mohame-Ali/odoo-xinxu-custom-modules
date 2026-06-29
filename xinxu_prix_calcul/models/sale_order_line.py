# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    x_supplier_id = fields.Many2one(
        comodel_name='res.partner',
        string='Supplier',
        domain=[('supplier_rank', '>=', 0)],
        help="Supplier selected after the comparison table.",
    )
    x_delivery_time = fields.Char(
        string='Delivery Time',
        help="Lead time given by the supplier (e.g. 2 Weeks, In Stock).",
    )
    x_supplier_price = fields.Float(
        string='Supplier Price',
        digits=(16, 4),
        default=0.0,
        help="Supplier purchase price. The computed sale price is written "
             "automatically into the order line Unit Price.",
    )
    x_conversion_rate = fields.Float(
        string='Conversion Rate',
        digits=(16, 6),
        default=1.0,
        help="Conversion rate to the quotation currency. "
             "To be entered manually (do not use the automatic rate).",
    )
    x_margin_pct = fields.Float(
        string='Margin (%)',
        digits=(5, 4),
        default=0.10,
        help="Commercial margin percentage. "
             "Local default 10%, Foreign default 13%.",
    )
    x_customs_duties_pct = fields.Float(
        string='Customs Duties (%)',
        digits=(5, 4),
        default=0.01,
        help="Customs duties applied on the supplier price. Default 1%.",
    )
    x_fodec_pct = fields.Float(
        string='FODEC (%)',
        digits=(5, 4),
        default=0.01,
        help="Competitiveness Development Fund. Default 1%.",
    )
    x_impot_douane_pct = fields.Float(
        string='Customs Tax (%)',
        digits=(5, 4),
        default=0.30,
        help="Tunisian customs tax. Default 30%.",
    )
    x_avance_import_pct = fields.Float(
        string='Import Advance (%)',
        digits=(5, 4),
        default=0.03,
        help="Advance on import tax. Default 3%.",
    )
    x_tva_pct = fields.Float(
        string='VAT (%)',
        digits=(5, 4),
        default=0.19,
        help="Tunisian VAT rate. Default 19%.",
    )

    # Computed - local table
    x_total_price_orig = fields.Float(
        string='Total Price (origin currency)',
        compute='_compute_local', store=True, digits=(16, 4),
        help="Supplier price x (1 + Customs Duties %).",
    )
    x_price_tnd = fields.Float(
        string='Price After Conversion',
        compute='_compute_local', store=True, digits=(16, 4),
        help="Total origin price x Conversion Rate.",
    )
    x_price_fodec = fields.Float(
        string='Price + FODEC',
        compute='_compute_local', store=True, digits=(16, 4),
        help="Price after conversion x (1 + FODEC %).",
    )
    x_price_all_taxes = fields.Float(
        string='Price With Customs Tax',
        compute='_compute_local', store=True, digits=(16, 4),
        help="Price + FODEC x (1 + Customs Tax %).",
    )
    x_total_cost_tnd = fields.Float(
        string='Total Cost',
        compute='_compute_local', store=True, digits=(16, 4),
        help="Price with all taxes x (1 + Import Advance %).",
    )
    x_prix_htva = fields.Float(
        string='Unit Price (excl. VAT)',
        compute='_compute_local', store=True, digits=(16, 4),
        help="Total cost / (1 - Margin %).",
    )
    x_marge_unitaire = fields.Float(
        string='Unit Margin (local)',
        compute='_compute_local', store=True, digits=(16, 4),
        help="Unit Price (excl. VAT) - Total cost.",
    )
    x_montant_tva = fields.Float(
        string='VAT Amount',
        compute='_compute_local', store=True, digits=(16, 4),
        help="Unit Price (excl. VAT) x VAT %.",
    )
    x_prix_ttc = fields.Float(
        string='Sale Price (incl. VAT)',
        compute='_compute_local', store=True, digits=(16, 4),
        help="Unit Price (excl. VAT) + VAT Amount -> CUSTOMER SALE PRICE.",
    )
    x_prix_total_ttc = fields.Float(
        string='Total Price (incl. VAT)',
        compute='_compute_local', store=True, digits=(16, 4),
        help="Sale Price (incl. VAT) x Quantity.",
    )
    x_marge_total_local = fields.Float(
        string='Total Margin (local)',
        compute='_compute_local', store=True, digits=(16, 4),
        help="Unit margin x Quantity.",
    )

    # Computed - foreign table
    x_price_eur = fields.Float(
        string='Converted Cost',
        compute='_compute_foreign', store=True, digits=(16, 4),
        help="Supplier price converted into the quotation currency.",
    )
    x_unit_sell_price_eur = fields.Float(
        string='Unit Sale Price (converted)',
        compute='_compute_foreign', store=True, digits=(16, 4),
        help="Unit sale price offered to the customer "
             "(converted cost / (1 - Margin %)).",
    )
    x_prix_total_eur = fields.Float(
        string='Suggested Sale Price',
        compute='_compute_foreign', store=True, digits=(16, 4),
        help="Line total = Quantity x suggested unit sale price.",
    )
    x_margin_value_eur = fields.Float(
        string='Unit Margin (foreign)',
        compute='_compute_foreign', store=True, digits=(16, 4),
        help="Margin per unit = suggested sale price - converted cost.",
    )
    x_marge_total_eur = fields.Float(
        string='Total Margin (foreign)',
        compute='_compute_foreign', store=True, digits=(16, 4),
        help="Total margin = unit margin x Quantity.",
    )

    @api.depends(
        'x_supplier_price', 'product_uom_qty', 'x_customs_duties_pct',
        'x_conversion_rate', 'x_fodec_pct', 'x_impot_douane_pct',
        'x_avance_import_pct', 'x_margin_pct', 'x_tva_pct',
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

            if line.order_id.xinxu_calc_type == 'local':
                line.price_unit = u

    @api.depends(
        'x_supplier_price', 'product_uom_qty', 'x_conversion_rate',
        'x_margin_pct', 'order_id.xinxu_calc_type',
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

            if line.order_id.xinxu_calc_type == 'foreign':
                line.price_unit = m
