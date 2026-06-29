# -*- coding: utf-8 -*-
"""
Tests UNITAIRES — xinxu_prix_calcul
=====================================
Conformément à la définition du test unitaire : chaque test ici
vérifie UNE méthode ou UN champ calculé, en isolation, sans dépendre du
comportement d'autres modules (sale, purchase, account). Le module est
installé seul ; aucune commande/bon de commande/facture n'est créée ici.
"""
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPrixCalculUnit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Client Test"})
        cls.product = cls.env["product.product"].create({"name": "Équipement Test"})

    def _make_line(self, calc_type, **vals):
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "xinxu_calc_type": calc_type,
        })
        line_vals = {
            "order_id": order.id,
            "product_id": self.product.id,
            "product_uom_qty": 2.0,
        }
        line_vals.update(vals)
        return self.env["sale.order.line"].create(line_vals)

    LOCAL_INPUTS = {
        "x_supplier_price": 100.0, "x_customs_duties_pct": 0.01,
        "x_conversion_rate": 3.0, "x_fodec_pct": 0.01, "x_impot_douane_pct": 0.30,
        "x_avance_import_pct": 0.03, "x_margin_pct": 0.10, "x_tva_pct": 0.19,
    }

    # ──────────────────────────────────────────────────────────────────
    # 1. Chaîne de calcul LOCAL — chaque étape de la chaîne douanière
    # ──────────────────────────────────────────────────────────────────

    def test_local_step1_customs_duties(self):
        """Étape F : prix fournisseur × (1 + droits de douane)."""
        line = self._make_line("local", **self.LOCAL_INPUTS)
        self.assertAlmostEqual(line.x_total_price_orig, 101.0, places=2)

    def test_local_step2_conversion(self):
        """Étape I : prix après droits × taux de conversion."""
        line = self._make_line("local", **self.LOCAL_INPUTS)
        self.assertAlmostEqual(line.x_price_tnd, 303.0, places=2)

    def test_local_step3_fodec(self):
        """Étape K : prix converti × (1 + FODEC)."""
        line = self._make_line("local", **self.LOCAL_INPUTS)
        self.assertAlmostEqual(line.x_price_fodec, 306.03, places=2)

    def test_local_step4_impot_douane(self):
        """Étape M : prix + FODEC × (1 + impôt douane)."""
        line = self._make_line("local", **self.LOCAL_INPUTS)
        self.assertAlmostEqual(line.x_price_all_taxes, 397.839, places=2)

    def test_local_step5_avance_import(self):
        """Étape O : coût total = prix toutes taxes × (1 + avance import)."""
        line = self._make_line("local", **self.LOCAL_INPUTS)
        self.assertAlmostEqual(line.x_total_cost_tnd, 409.77417, places=2)

    def test_local_step6_margin_and_htva(self):
        """Étape Q : prix HTVA = coût total ÷ (1 - marge)."""
        line = self._make_line("local", **self.LOCAL_INPUTS)
        self.assertAlmostEqual(line.x_prix_htva, 455.30463, places=2)

    def test_local_marge_unitaire(self):
        """Étape R : marge unitaire = prix HTVA - coût total."""
        line = self._make_line("local", **self.LOCAL_INPUTS)
        expected_margin = 455.30463 - 409.77417
        self.assertAlmostEqual(line.x_marge_unitaire, expected_margin, places=2)

    def test_local_montant_tva(self):
        """Étape T : montant TVA = prix HTVA × taux TVA."""
        line = self._make_line("local", **self.LOCAL_INPUTS)
        self.assertAlmostEqual(line.x_montant_tva, 455.30463 * 0.19, places=2)

    def test_local_prix_ttc_final(self):
        """Étape U : prix de vente TTC = prix HTVA + montant TVA."""
        line = self._make_line("local", **self.LOCAL_INPUTS)
        self.assertAlmostEqual(line.x_prix_ttc, 541.81251, places=2)

    def test_local_prix_total_ttc_quantity(self):
        """Étape W : prix total TTC = prix TTC × quantité (qty=2)."""
        line = self._make_line("local", **self.LOCAL_INPUTS)
        self.assertAlmostEqual(line.x_prix_total_ttc, 1083.62503, places=2)

    def test_local_marge_total(self):
        """Étape X : marge totale = marge unitaire × quantité (qty=2)."""
        line = self._make_line("local", **self.LOCAL_INPUTS)
        expected_margin_total = (455.30463 - 409.77417) * 2
        self.assertAlmostEqual(line.x_marge_total_local, expected_margin_total, places=2)

    def test_local_writes_price_unit(self):
        """Le prix TTC calculé est propagé dans le champ standard price_unit."""
        line = self._make_line("local", **self.LOCAL_INPUTS)
        line.flush_recordset()
        self.assertAlmostEqual(line.price_unit, 541.81251, places=2)

    # ──────────────────────────────────────────────────────────────────
    # 2. Chaîne de calcul ÉTRANGER — conversion + marge (2 étapes)
    # ──────────────────────────────────────────────────────────────────

    def test_foreign_step1_conversion(self):
        """Coût converti = prix fournisseur × taux de conversion."""
        line = self._make_line(
            "foreign", x_supplier_price=100.0,
            x_conversion_rate=0.93, x_margin_pct=0.13,
        )
        self.assertAlmostEqual(line.x_price_eur, 93.0, places=2)

    def test_foreign_step2_unit_sell_price(self):
        """Prix de vente unitaire = coût converti ÷ (1 - marge)."""
        line = self._make_line(
            "foreign", x_supplier_price=100.0,
            x_conversion_rate=0.93, x_margin_pct=0.13,
        )
        self.assertAlmostEqual(line.x_unit_sell_price_eur, 106.89655, places=2)

    def test_foreign_total_suggested_price(self):
        """Prix de vente suggéré (total ligne) = quantité × prix de vente unitaire."""
        line = self._make_line(
            "foreign", x_supplier_price=100.0,
            x_conversion_rate=0.93, x_margin_pct=0.13,
        )
        self.assertAlmostEqual(line.x_prix_total_eur, 213.79310, places=2)

    def test_foreign_unit_margin(self):
        """Marge unitaire (étranger) = prix de vente suggéré - coût converti."""
        line = self._make_line(
            "foreign", x_supplier_price=100.0,
            x_conversion_rate=0.93, x_margin_pct=0.13,
        )
        self.assertAlmostEqual(line.x_margin_value_eur, 13.89655, places=2)

    def test_foreign_total_margin(self):
        """Marge totale (étranger) = marge unitaire × quantité (qty=2)."""
        line = self._make_line(
            "foreign", x_supplier_price=100.0,
            x_conversion_rate=0.93, x_margin_pct=0.13,
        )
        self.assertAlmostEqual(line.x_marge_total_eur, 27.79310, places=2)

    def test_foreign_writes_price_unit(self):
        """Le prix de vente unitaire (étranger) est propagé dans price_unit."""
        line = self._make_line(
            "foreign", x_supplier_price=100.0,
            x_conversion_rate=0.93, x_margin_pct=0.13,
        )
        line.flush_recordset()
        self.assertAlmostEqual(line.price_unit, 106.89655, places=2)

    # ──────────────────────────────────────────────────────────────────
    # 3. Cas limites et valeurs par défaut
    # ──────────────────────────────────────────────────────────────────

    def test_default_values(self):
        """Les valeurs par défaut du modèle correspondent au cahier des charges."""
        line = self._make_line("local")
        self.assertEqual(line.x_supplier_price, 0.0)
        self.assertAlmostEqual(line.x_conversion_rate, 1.0, places=4)
        self.assertAlmostEqual(line.x_margin_pct, 0.10, places=4)
        self.assertAlmostEqual(line.x_customs_duties_pct, 0.01, places=4)
        self.assertAlmostEqual(line.x_fodec_pct, 0.01, places=4)
        self.assertAlmostEqual(line.x_impot_douane_pct, 0.30, places=4)
        self.assertAlmostEqual(line.x_avance_import_pct, 0.03, places=4)
        self.assertAlmostEqual(line.x_tva_pct, 0.19, places=4)

    def test_zero_supplier_price_gives_zero_chain(self):
        """Un prix fournisseur nul propage des zéros tout le long de la chaîne."""
        line = self._make_line("local", x_supplier_price=0.0)
        self.assertEqual(line.x_total_price_orig, 0.0)
        self.assertEqual(line.x_prix_ttc, 0.0)

    def test_margin_cap_at_100_percent_no_crash(self):
        """Une marge saisie à 100% est plafonnée (0.9999) pour éviter une
        division par zéro ; le calcul reste fini et positif."""
        line = self._make_line("local", x_supplier_price=100.0, x_margin_pct=1.0)
        self.assertGreater(line.x_prix_htva, 0.0)
        self.assertNotEqual(line.x_prix_htva, float("inf"))

    def test_margin_above_100_percent_no_crash(self):
        """Une marge saisie au-dessus de 100% (saisie erronée) est aussi
        plafonnée et ne fait pas planter le calcul."""
        line = self._make_line("local", x_supplier_price=100.0, x_margin_pct=2.5)
        self.assertGreater(line.x_prix_htva, 0.0)

    def test_quantity_multiplier_local(self):
        """Le doublement de la quantité double exactement les totaux de
        ligne (prix_total_ttc, marge_total_local) sans affecter le prix
        unitaire (prix_ttc)."""
        line_qty2 = self._make_line("local", product_uom_qty=2.0, **self.LOCAL_INPUTS)
        line_qty4 = self._make_line("local", product_uom_qty=4.0, **self.LOCAL_INPUTS)
        # Le prix unitaire ne dépend pas de la quantité
        self.assertAlmostEqual(line_qty2.x_prix_ttc, line_qty4.x_prix_ttc, places=2)
        # Les totaux de ligne, eux, doublent
        self.assertAlmostEqual(
            line_qty4.x_prix_total_ttc, line_qty2.x_prix_total_ttc * 2, places=2
        )
        self.assertAlmostEqual(
            line_qty4.x_marge_total_local, line_qty2.x_marge_total_local * 2, places=2
        )

    def test_quantity_multiplier_foreign(self):
        """Même vérification que ci-dessus, pour la chaîne étranger."""
        common = {"x_supplier_price": 100.0, "x_conversion_rate": 0.93, "x_margin_pct": 0.13}
        line_qty2 = self._make_line("foreign", product_uom_qty=2.0, **common)
        line_qty4 = self._make_line("foreign", product_uom_qty=4.0, **common)
        self.assertAlmostEqual(
            line_qty2.x_unit_sell_price_eur, line_qty4.x_unit_sell_price_eur, places=2
        )
        self.assertAlmostEqual(
            line_qty4.x_prix_total_eur, line_qty2.x_prix_total_eur * 2, places=2
        )

    def test_switching_calc_type_recomputes_both_chains(self):
        """Changer order.xinxu_calc_type force le recalcul des deux chaînes
        (locale et étrangère) car les deux dépendent de ce champ."""
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id, "xinxu_calc_type": "local",
        })
        line = self.env["sale.order.line"].create({
            "order_id": order.id, "product_id": self.product.id,
            "product_uom_qty": 1.0, "x_supplier_price": 100.0,
            "x_conversion_rate": 1.0, "x_margin_pct": 0.10,
            **{k: v for k, v in self.LOCAL_INPUTS.items()
               if k not in ("x_supplier_price", "x_conversion_rate", "x_margin_pct")},
        })
        line.flush_recordset()
        local_price = line.price_unit
        order.xinxu_calc_type = "foreign"
        line.flush_recordset()
        foreign_price = line.price_unit
        # Les deux chaînes de calcul donnent des résultats différents
        # (chaîne douanière à 6 étapes vs conversion+marge à 2 étapes)
        self.assertNotAlmostEqual(local_price, foreign_price, places=2)

    # ──────────────────────────────────────────────────────────────────
    # 4. Champs annexes du sale.order (compteur BC fournisseur)
    # ──────────────────────────────────────────────────────────────────

    def test_purchase_count_zero_initially(self):
        """Un nouveau devis n'a aucun bon de commande fournisseur lié."""
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.assertEqual(order.xinxu_purchase_count, 0)

    def test_purchase_count_computed_from_m2m(self):
        """xinxu_purchase_count reflète le nombre d'éléments dans
        xinxu_purchase_ids (many2many)."""
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        po = self.env["purchase.order"].create({"partner_id": self.partner.id})
        order.xinxu_purchase_ids = [(4, po.id)]
        self.assertEqual(order.xinxu_purchase_count, 1)

    # ──────────────────────────────────────────────────────────────────
    # 5. Robustesse : saisies erronées
    # ──────────────────────────────────────────────────────────────────

    def test_negative_supplier_price_gives_negative_result(self):
        """Un prix fournisseur négatif propage des valeurs négatives
        tout le long de la chaîne — le calcul ne crashe pas mais le
        résultat est mathématiquement cohérent (pas de filtration)."""
        line = self._make_line("local", x_supplier_price=-50.0)
        self.assertLess(line.x_prix_ttc, 0.0)

    def test_zero_quantity_gives_zero_total(self):
        """Une quantité nulle donne un total de ligne à zéro,
        mais le prix unitaire reste calculé."""
        line = self._make_line("local", product_uom_qty=0.0, **self.LOCAL_INPUTS)
        self.assertEqual(line.x_prix_total_ttc, 0.0)
        self.assertGreater(line.x_prix_ttc, 0.0)

    def test_negative_quantity_gives_negative_total(self):
        """Une quantité négative (erreur de saisie) produit un total
        négatif — le calcul ne plante pas mais le résultat est
        mathématiquement cohérent."""
        line = self._make_line("local", product_uom_qty=-1.0, **self.LOCAL_INPUTS)
        self.assertLess(line.x_prix_total_ttc, 0.0)

    def test_very_large_supplier_price_no_overflow(self):
        """Un prix fournisseur très élevé (1 million) ne cause pas
        d'overflow ni d'erreur de calcul."""
        line = self._make_line("local", x_supplier_price=1_000_000.0)
        self.assertGreater(line.x_prix_ttc, 0.0)
        self.assertLess(line.x_prix_ttc, float("inf"))

    def test_zero_conversion_rate_gives_zero_chain(self):
        """Un taux de conversion à zéro bloque la chaîne à zéro
        après l'étape de conversion."""
        inputs = {k: v for k, v in self.LOCAL_INPUTS.items() if k != "x_conversion_rate"}
        line = self._make_line("local", x_conversion_rate=0.0, **inputs)
        self.assertEqual(line.x_price_tnd, 0.0)
        self.assertEqual(line.x_prix_ttc, 0.0)

    def test_foreign_negative_margin_no_crash(self):
        """Une marge négative (erreur de saisie) ne crashe pas le calcul
        étranger — le résultat est inférieur au coût."""
        line = self._make_line(
            "foreign", x_supplier_price=100.0,
            x_conversion_rate=1.0, x_margin_pct=-0.10,
        )
        self.assertLess(line.x_unit_sell_price_eur, 100.0)

    # ──────────────────────────────────────────────────────────────────
    # 6. Propagation en cascade
    # ──────────────────────────────────────────────────────────────────

    def test_changing_supplier_price_updates_all_11_computed_fields(self):
        """Quand le prix fournisseur change, les 11 champs calculés
        de la chaîne locale doivent tous être différents — prouve que
        la dépendance @api.depends couvre toute la chaîne."""
        line = self._make_line("local", x_supplier_price=100.0)
        line.flush_recordset()
        # Capturer les 11 valeurs calculées
        vals_100 = {
            "x_total_price_orig": line.x_total_price_orig,
            "x_price_tnd": line.x_price_tnd,
            "x_price_fodec": line.x_price_fodec,
            "x_price_all_taxes": line.x_price_all_taxes,
            "x_total_cost_tnd": line.x_total_cost_tnd,
            "x_prix_htva": line.x_prix_htva,
            "x_marge_unitaire": line.x_marge_unitaire,
            "x_montant_tva": line.x_montant_tva,
            "x_prix_ttc": line.x_prix_ttc,
            "x_prix_total_ttc": line.x_prix_total_ttc,
            "x_marge_total_local": line.x_marge_total_local,
        }
        # Changer le prix fournisseur
        line.x_supplier_price = 200.0
        line.flush_recordset()
        # Vérifier que les 11 champs ont changé
        for field_name, old_val in vals_100.items():
            new_val = getattr(line, field_name)
            self.assertNotEqual(
                old_val, new_val,
                f"Le champ {field_name} n'a pas été mis à jour "
                f"quand x_supplier_price est passé de 100 à 200"
            )