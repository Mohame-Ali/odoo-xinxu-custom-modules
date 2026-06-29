# -*- coding: utf-8 -*-
"""
Tests DE SYSTÈME — xinxu_prix_calcul
=======================================
Conformément à la définition du test de système (2.9.3) : chaque test
ici exécute un cycle complet, de la création du devis jusqu'à la
facture, en passant par toutes les étapes intermédiaires réelles
(calcul du prix, confirmation du devis, création du bon de commande
fournisseur, facturation). Aucune étape n'est court-circuitée : on
appelle les mêmes méthodes que celles déclenchées par les boutons de
l'interface utilisateur.
"""
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPrixCalculSystem(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({
            "name": "Pompe industrielle", "invoice_policy": "order",
        })
        cls.client_local = cls.env["res.partner"].create({"name": "Client Tunisien"})
        cls.client_etranger = cls.env["res.partner"].create({"name": "Client Européen"})
        cls.supplier = cls.env["res.partner"].create({"name": "Fournisseur Chine"})

    def test_full_cycle_local_devis_to_facture(self):
        """Cycle complet — client local :
        1. Création du devis avec une ligne de calcul (type local)
        2. Vérification du prix de vente calculé (chaîne douanière)
        3. Confirmation du devis (devis -> commande de vente)
        4. Création du bon de commande fournisseur
        5. Vérification du lien BC <-> devis
        6. Facturation du client
        7. Vérification du montant facturé = prix calculé
        """
        # 1. Création du devis
        order = self.env["sale.order"].create({
            "partner_id": self.client_local.id,
            "xinxu_calc_type": "local",
            "xinxu_delivery_mode": "Rendu Tunis",
        })
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.product.id,
            "product_uom_qty": 5.0,
            "x_supplier_id": self.supplier.id,
            "x_supplier_price": 200.0,
            "x_customs_duties_pct": 0.01,
            "x_conversion_rate": 3.1,
            "x_fodec_pct": 0.01,
            "x_impot_douane_pct": 0.30,
            "x_avance_import_pct": 0.03,
            "x_margin_pct": 0.15,
            "x_tva_pct": 0.19,
        })
        line.flush_recordset()

        # 2. Vérification du prix calculé (chaîne complète)
        expected_ttc = line.x_prix_ttc
        self.assertGreater(expected_ttc, 0)
        self.assertAlmostEqual(order.order_line.price_unit, expected_ttc, places=2)
        self.assertEqual(order.state, "draft")

        # 3. Confirmation du devis
        order.action_confirm()
        self.assertEqual(order.state, "sale")
        # Le prix calculé ne doit pas changer après confirmation
        self.assertAlmostEqual(order.order_line.price_unit, expected_ttc, places=2)

        # 4. Création du bon de commande fournisseur
        order.action_xinxu_create_purchase_order()
        po = self.env["purchase.order"].search([("origin", "=", order.name)])
        self.assertEqual(len(po), 1)
        self.assertEqual(po.partner_id, self.supplier)
        self.assertAlmostEqual(po.order_line.price_unit, 200.0, places=2)
        self.assertEqual(po.order_line.product_qty, 5.0)

        # 5. Vérification du lien BC <-> devis (traçabilité bidirectionnelle)
        self.assertIn(po, order.xinxu_purchase_ids)
        self.assertEqual(order.xinxu_purchase_count, 1)

        # 6. Facturation du client (le montant facturé reprend price_unit)
        invoice = order._create_invoices()
        self.assertEqual(invoice.partner_id, self.client_local)
        self.assertAlmostEqual(
            invoice.invoice_line_ids[0].price_unit, expected_ttc, places=2
        )
        # 7. Le montant total facturé correspond au prix calculé × quantité
        self.assertAlmostEqual(invoice.amount_untaxed, expected_ttc * 5.0, places=2)

    def test_full_cycle_foreign_devis_to_facture(self):
        """Même cycle complet, client étranger : devis -> calcul (chaîne
        conversion+marge) -> confirmation -> BC fournisseur -> facture."""
        order = self.env["sale.order"].create({
            "partner_id": self.client_etranger.id,
            "xinxu_calc_type": "foreign",
        })
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.product.id,
            "product_uom_qty": 10.0,
            "x_supplier_id": self.supplier.id,
            "x_supplier_price": 80.0,
            "x_conversion_rate": 0.91,
            "x_margin_pct": 0.18,
        })
        line.flush_recordset()
        expected_unit_price = line.x_unit_sell_price_eur
        self.assertAlmostEqual(order.order_line.price_unit, expected_unit_price, places=2)

        order.action_confirm()
        self.assertEqual(order.state, "sale")

        order.action_xinxu_create_purchase_order()
        po = self.env["purchase.order"].search([("origin", "=", order.name)])
        self.assertAlmostEqual(po.order_line.price_unit, 80.0, places=2)

        invoice = order._create_invoices()
        self.assertAlmostEqual(
            invoice.invoice_line_ids[0].price_unit, expected_unit_price, places=2
        )
        # Tolérance à 1 décimale (et non 2) : x_unit_sell_price_eur est
        # stocké avec 4 décimales de précision, alors qu'Odoo arrondit
        # amount_untaxed à la précision de la devise (généralement 2
        # décimales) APRÈS multiplication par la quantité. Un écart de
        # quelques millièmes entre les deux est donc normal, pas une
        # erreur de calcul.
        self.assertAlmostEqual(
            invoice.amount_untaxed, expected_unit_price * 10.0, places=1
        )

    def test_full_cycle_multi_supplier_multi_line(self):
        """Cycle complet réaliste : un devis avec plusieurs lignes, deux
        fournisseurs distincts. Vérifie que le cycle complet (devis ->
        confirmation -> BC -> facture) gère correctement le regroupement
        par fournisseur tout en facturant la totalité de la commande au
        client final."""
        supplier_2 = self.env["res.partner"].create({"name": "Fournisseur Allemagne"})
        product_2 = self.env["product.product"].create({
            "name": "Vanne industrielle", "invoice_policy": "order",
        })

        order = self.env["sale.order"].create({
            "partner_id": self.client_local.id, "xinxu_calc_type": "local",
        })
        line1 = self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": self.product.id,
            "product_uom_qty": 2.0, "x_supplier_id": self.supplier.id,
            "x_supplier_price": 150.0, "x_margin_pct": 0.10,
        })
        line2 = self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": product_2.id,
            "product_uom_qty": 3.0, "x_supplier_id": supplier_2.id,
            "x_supplier_price": 90.0, "x_margin_pct": 0.10,
        })
        line1.flush_recordset()
        line2.flush_recordset()
        total_expected = line1.x_prix_total_ttc + line2.x_prix_total_ttc

        order.action_confirm()
        order.action_xinxu_create_purchase_order()

        # Deux BC distincts, un par fournisseur
        pos = self.env["purchase.order"].search([("origin", "=", order.name)])
        self.assertEqual(len(pos), 2)
        self.assertEqual(order.xinxu_purchase_count, 2)

        # La facture client regroupe les deux lignes, peu importe le
        # nombre de fournisseurs en amont
        invoice = order._create_invoices()
        self.assertEqual(len(invoice.invoice_line_ids), 2)
        self.assertAlmostEqual(invoice.amount_untaxed, total_expected, places=2)

    def test_cycle_blocked_if_po_attempted_before_confirmation(self):
        """Test de système négatif : le cycle business interdit de créer
        un bon de commande fournisseur tant que le client n'a pas
        confirmé le devis — vérifie que l'ordre des étapes du cycle est
        respecté de bout en bout."""
        from odoo.exceptions import UserError
        order = self.env["sale.order"].create({
            "partner_id": self.client_local.id, "xinxu_calc_type": "local",
        })
        self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": self.product.id,
            "product_uom_qty": 1.0, "x_supplier_id": self.supplier.id,
            "x_supplier_price": 100.0,
        })
        # Étape 4 tentée avant l'étape 3 (confirmation) : doit échouer
        with self.assertRaises(UserError):
            order.action_xinxu_create_purchase_order()
        # Le cycle correct fonctionne ensuite normalement
        order.action_confirm()
        order.action_xinxu_create_purchase_order()  # ne lève plus d'erreur
        self.assertEqual(order.xinxu_purchase_count, 1)
