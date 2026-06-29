# -*- coding: utf-8 -*-
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestPrixCalculE2E(HttpCase):
    """Tour E2E : création devis → Tableau de Calcul → vérification TTC → confirmation."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Client requis pour action_confirm
        cls.env["res.partner"].create({"name": "XINXU E2E Client"})
        # Produit SANS variantes → le configurateur modal ne s'ouvrira jamais
        cls.env["product.product"].create({
            "name": "XINXU E2E Product",
            "sale_ok": True,
            "purchase_ok": True,
        })

    def test_01_xinxu_prix_calcul_tour(self):
        self.start_tour("/odoo/sales", "xinxu_prix_calcul_tour", login="admin")

    def test_02_xinxu_prix_calcul_tour_foreign(self):
        self.start_tour("/odoo/sales", "xinxu_prix_calcul_tour_foreign", login="admin")