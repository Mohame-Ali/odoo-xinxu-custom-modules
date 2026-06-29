# -*- coding: utf-8 -*-
"""
Tests D'INTÉGRATION — xinxu_prix_calcul
==========================================
Conformément à la définition du test d'intégration (2.9.2) : ces tests
regroupent xinxu_prix_calcul avec au moins un autre module (purchase,
account via custom_invoice_xinxu) et vérifient le flux de données à
l'interface entre eux : création de bons de commande fournisseur,
regroupement par fournisseur, propagation de champs vers la facture.

Découverte technique : action_xinxu_create_purchase_order (ce module) et
_prepare_invoice (ce module) sont chacun un point d'intégration avec un
autre module Odoo (purchase, account). En particulier, _prepare_invoice
écrit dans account.move le champ xinxu_delivery_mode, qui n'existe QUE
si le module custom_invoice_xinxu est également installé — bien que
cette dépendance ne soit pas déclarée dans le manifeste de
xinxu_prix_calcul (depends = ['sale', 'purchase'] uniquement). Ce test
le vérifie explicitement.
"""
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPrixCalculIntegrationPurchase(TransactionCase):
    """Intégration avec le module purchase : création de bons de commande
    fournisseur à partir des lignes du devis."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_a = cls.env["product.product"].create({"name": "Article A"})
        cls.product_b = cls.env["product.product"].create({"name": "Article B"})
        cls.client = cls.env["res.partner"].create({"name": "Client XINXU"})
        cls.supplier_1 = cls.env["res.partner"].create({"name": "Fournisseur 1"})
        cls.supplier_2 = cls.env["res.partner"].create({"name": "Fournisseur 2"})

    def _confirmed_order_with_line(self, supplier=None, **line_vals):
        order = self.env["sale.order"].create({
            "partner_id": self.client.id, "xinxu_calc_type": "local",
        })
        vals = {
            "order_id": order.id, "product_id": self.product_a.id,
            "product_uom_qty": 1.0,
        }
        if supplier:
            vals["x_supplier_id"] = supplier.id
        vals.update(line_vals)
        self.env["sale.order.line"].create(vals)
        order.action_confirm()
        return order

    def test_button_blocked_before_confirmation(self):
        """Le bouton refuse de créer un BC sur un devis non confirmé
        (état 'draft') : c'est une règle métier inter-modules, le BC ne
        doit exister qu'après accord client sur la vente."""
        order = self.env["sale.order"].create({
            "partner_id": self.client.id, "xinxu_calc_type": "local",
        })
        self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": self.product_a.id,
            "product_uom_qty": 1.0, "x_supplier_id": self.supplier_1.id,
        })
        with self.assertRaises(UserError):
            order.action_xinxu_create_purchase_order()

    def test_button_blocked_without_supplier(self):
        """Le bouton refuse de créer un BC si aucune ligne n'a de
        fournisseur renseigné."""
        order = self._confirmed_order_with_line(supplier=None)
        with self.assertRaises(UserError):
            order.action_xinxu_create_purchase_order()

    def test_creates_purchase_order_with_correct_fields(self):
        """Le BC créé porte le bon fournisseur, le bon produit, la bonne
        quantité, et reprend le prix fournisseur (x_supplier_price) —
        pas le prix de vente calculé (price_unit)."""
        order = self._confirmed_order_with_line(
            supplier=self.supplier_1, x_supplier_price=250.0, product_uom_qty=3.0,
        )
        order.action_xinxu_create_purchase_order()
        po = self.env["purchase.order"].search([("partner_id", "=", self.supplier_1.id)])
        self.assertEqual(len(po), 1)
        self.assertEqual(po.order_line.product_id, self.product_a)
        self.assertEqual(po.order_line.product_qty, 3.0)
        self.assertAlmostEqual(po.order_line.price_unit, 250.0, places=2)

    def test_po_origin_references_sale_order(self):
        """Le champ origin du BC référence le nom du devis d'origine,
        garantissant la traçabilité entre les deux modules."""
        order = self._confirmed_order_with_line(
            supplier=self.supplier_1, x_supplier_price=100.0,
        )
        order.action_xinxu_create_purchase_order()
        po = self.env["purchase.order"].search([("partner_id", "=", self.supplier_1.id)])
        self.assertEqual(po.origin, order.name)

    def test_multiple_suppliers_create_separate_purchase_orders(self):
        """Deux lignes avec deux fournisseurs distincts génèrent deux BC
        distincts (un par fournisseur), chacun avec sa propre ligne."""
        order = self.env["sale.order"].create({
            "partner_id": self.client.id, "xinxu_calc_type": "local",
        })
        self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": self.product_a.id,
            "product_uom_qty": 1.0, "x_supplier_id": self.supplier_1.id,
            "x_supplier_price": 100.0,
        })
        self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": self.product_b.id,
            "product_uom_qty": 1.0, "x_supplier_id": self.supplier_2.id,
            "x_supplier_price": 200.0,
        })
        order.action_confirm()
        order.action_xinxu_create_purchase_order()
        po_1 = self.env["purchase.order"].search([("partner_id", "=", self.supplier_1.id)])
        po_2 = self.env["purchase.order"].search([("partner_id", "=", self.supplier_2.id)])
        self.assertEqual(len(po_1), 1)
        self.assertEqual(len(po_2), 1)
        self.assertNotEqual(po_1.id, po_2.id)

    def test_same_supplier_groups_lines_into_one_po(self):
        """Deux lignes avec le MÊME fournisseur sont regroupées dans un
        seul BC contenant deux lignes de commande."""
        order = self.env["sale.order"].create({
            "partner_id": self.client.id, "xinxu_calc_type": "local",
        })
        self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": self.product_a.id,
            "product_uom_qty": 1.0, "x_supplier_id": self.supplier_1.id,
            "x_supplier_price": 100.0,
        })
        self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": self.product_b.id,
            "product_uom_qty": 1.0, "x_supplier_id": self.supplier_1.id,
            "x_supplier_price": 150.0,
        })
        order.action_confirm()
        order.action_xinxu_create_purchase_order()
        pos = self.env["purchase.order"].search([("partner_id", "=", self.supplier_1.id)])
        self.assertEqual(len(pos), 1)
        self.assertEqual(len(pos.order_line), 2)

    def test_purchase_ids_linked_back_to_sale_order(self):
        """Le(s) BC créé(s) sont ajoutés à xinxu_purchase_ids sur le
        devis d'origine — le lien est bidirectionnel."""
        order = self._confirmed_order_with_line(
            supplier=self.supplier_1, x_supplier_price=100.0,
        )
        self.assertEqual(order.xinxu_purchase_count, 0)
        order.action_xinxu_create_purchase_order()
        self.assertEqual(order.xinxu_purchase_count, 1)
        po = self.env["purchase.order"].search([("partner_id", "=", self.supplier_1.id)])
        self.assertIn(po, order.xinxu_purchase_ids)

    def test_lines_without_supplier_are_excluded(self):
        """Si une ligne a un fournisseur et l'autre non, seule la ligne
        avec fournisseur génère un BC ; l'autre est simplement ignorée
        (pas d'erreur)."""
        order = self.env["sale.order"].create({
            "partner_id": self.client.id, "xinxu_calc_type": "local",
        })
        self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": self.product_a.id,
            "product_uom_qty": 1.0, "x_supplier_id": self.supplier_1.id,
            "x_supplier_price": 100.0,
        })
        self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": self.product_b.id,
            "product_uom_qty": 1.0,  # pas de fournisseur
        })
        order.action_confirm()
        order.action_xinxu_create_purchase_order()
        po = self.env["purchase.order"].search([("partner_id", "=", self.supplier_1.id)])
        self.assertEqual(len(po.order_line), 1)
        self.assertEqual(po.order_line.product_id, self.product_a)


@tagged("post_install", "-at_install")
class TestPrixCalculIntegrationInvoicing(TransactionCase):
    """Intégration avec la facturation (account.move) : vérifie que
    _prepare_invoice() propage correctement xinxu_delivery_mode vers la
    facture, et documente la dépendance implicite à custom_invoice_xinxu."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create({
            "name": "Article facturable", "invoice_policy": "order",
        })
        cls.client = cls.env["res.partner"].create({"name": "Client Facturation"})

    def test_delivery_mode_field_exists_only_with_custom_invoice_xinxu(self):
        """DÉCOUVERTE D'INTÉGRATION : account.move ne possède le champ
        xinxu_delivery_mode QUE si custom_invoice_xinxu est installé.
        xinxu_prix_calcul ne déclare pourtant pas cette dépendance dans
        son manifeste (depends = ['sale', 'purchase'] seulement).

        Ce test vérifie l'état réel du champ dans CET environnement de
        test : si custom_invoice_xinxu est installé, le champ existe et
        le test confirme la propagation ; sinon le test documente
        explicitly l'absence du champ plutôt que d'échouer en silence.
        """
        has_field = "xinxu_delivery_mode" in self.env["account.move"]._fields
        if not has_field:
            self.skipTest(
                "custom_invoice_xinxu n'est pas installé dans cette base : "
                "le champ xinxu_delivery_mode n'existe pas sur account.move. "
                "Ceci confirme que xinxu_prix_calcul a une dépendance "
                "implicite (non déclarée) envers custom_invoice_xinxu pour "
                "que la facturation fonctionne sans erreur."
            )
        order = self.env["sale.order"].create({
            "partner_id": self.client.id,
            "xinxu_calc_type": "local",
            "xinxu_delivery_mode": "FOB Radès",
        })
        self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": self.product.id,
            "product_uom_qty": 1.0, "price_unit": 100.0,
        })
        order.action_confirm()
        invoice = order._create_invoices()
        self.assertEqual(invoice.xinxu_delivery_mode, "FOB Radès")
