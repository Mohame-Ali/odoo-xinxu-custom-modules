#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generateur automatique de rapport PDF à partir de la sortie des tests Odoo.

Usage :
    # 1. Lancer les tests en capturant la sortie :
    ./odoo-bin -c /etc/odoo.conf -d test_xinxu -u xinxu_prix_calcul \
        --test-tags /xinxu_prix_calcul --stop-after-init 2>&1 | tee /tmp/test_results.log

    # 2. Generer le rapport :
    python3 generate_test_report.py /tmp/test_results.log

    # Le PDF est créé dans le meme dossier que le log.
"""
import re
import sys
import os
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, KeepTogether, Flowable,
    )
    from reportlab.graphics.shapes import Drawing, Rect, String
except ImportError:
    print("reportlab n'est pas installe. Installation en cours...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "reportlab", "--break-system-packages", "-q"])
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, white
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, KeepTogether, Flowable,
    )
    from reportlab.graphics.shapes import Drawing, Rect, String


# ─── FONTS (register DejaVu for unicode checkmark) ───
def _register_fonts():
    try:
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfbase import pdfmetrics as _pm
        if 'DejaVu' not in _pm.getRegisteredFontNames():
            _pm.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    except Exception:
        pass


# ─── COLORS ───
BLUE = HexColor("#1B3A5C")
LIGHT = HexColor("#E8EEF4")
GREEN = HexColor("#27AE60")
RED = HexColor("#E74C3C")
ORANGE = HexColor("#F39C12")
GRAY = HexColor("#7F8C8D")
DARK = HexColor("#2C3E50")
TERMINAL_BG = HexColor("#1A1A2E")
GREEN_BG = HexColor("#EAF7EF")
BLUE2 = HexColor("#2E86C1")
BLUE3 = HexColor("#5DADE2")
BLUE4 = HexColor("#85C1E9")


# ─── PARSE THE LOG ───
def parse_log(filepath):
    """Parse an Odoo test log and extract structured results."""
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    results = {
        'tests': [],
        'tours': [],
        'summary': {},
        'date': None,
        'duration': None,
        'queries': None,
        'odoo_version': None,
        'module': None,
        'raw_summary_line': '',
    }

    # Patterns
    p_start = re.compile(
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+.*Starting (\w+)\.(\w+)\s*\.\.\.'
    )
    p_error = re.compile(r'ERROR.*(?:ERROR|FAIL):\s*(\w+)\.(\w+)')
    p_skip = re.compile(r'skipped (\w+)\.(\w+)\s*:\s*(.*)')
    p_tour_ok = re.compile(r'TOUR (\S+) SUCCEEDED')
    p_tour_fail = re.compile(r'FAILED:.*Tour (\S+)')
    p_summary = re.compile(
        r'(\d+) failed, (\d+) error\(s\) of (\d+) tests'
    )
    p_duration = re.compile(r'(\d+) post-tests in ([\d.]+)s, (\d+) queries')
    p_version = re.compile(r'Odoo version (\S+)')
    p_module = re.compile(r'Loading module (\S+)')

    failed_set = set()
    skipped_set = set()

    for line in lines:
        # Odoo version
        m = p_version.search(line)
        if m and not results['odoo_version']:
            results['odoo_version'] = m.group(1)

        # Module name
        m = p_module.search(line)
        if m:
            results['module'] = m.group(1)

        # Test start
        m = p_start.search(line)
        if m:
            dt_str, class_name, method_name = m.group(1), m.group(2), m.group(3)
            if not results['date']:
                results['date'] = dt_str.split(' ')[0]
            results['tests'].append({
                'class': class_name,
                'method': method_name,
                'status': 'PASS',  # default, overridden if error/skip found
                'détail': '',
            })

        # Error or fail
        m = p_error.search(line)
        if m:
            key = (m.group(1), m.group(2))
            failed_set.add(key)

        # Skip
        m = p_skip.search(line)
        if m:
            key = (m.group(1), m.group(2))
            skipped_set.add(key)
            reason = m.group(3).strip()
            # Find matching test and update
            for t in results['tests']:
                if t['class'] == m.group(1) and t['method'] == m.group(2):
                    t['détail'] = reason

        # Tour success
        m = p_tour_ok.search(line)
        if m:
            results['tours'].append({'name': m.group(1), 'status': 'PASS'})

        # Tour fail
        m = p_tour_fail.search(line)
        if m:
            tour_name = m.group(1)
            # Only add if not already added as success
            existing = [t for t in results['tours'] if t['name'] == tour_name]
            if not existing:
                results['tours'].append({'name': tour_name, 'status': 'FAIL'})

        # Summary line
        m = p_summary.search(line)
        if m:
            results['summary'] = {
                'failed': int(m.group(1)),
                'errors': int(m.group(2)),
                'total': int(m.group(3)),
            }
            results['raw_summary_line'] = line.strip()

        # Duration
        m = p_duration.search(line)
        if m:
            results['duration'] = float(m.group(2))
            results['queries'] = int(m.group(3))

    # Mark failed and skipped tests
    for t in results['tests']:
        key = (t['class'], t['method'])
        if key in failed_set:
            t['status'] = 'FAIL'
        elif key in skipped_set:
            t['status'] = 'SKIP'

    return results


# ─── CATEGORIZE TESTS ───
def categorize(tests):
    """Group tests into the 4 levels based on class/method naming."""
    cats = {
        'unit': [],
        'integration': [],
        'system': [],
        'e2e': [],
    }
    for t in tests:
        cl = t['class'].lower()
        mt = t['method'].lower()
        if 'e2e' in cl or 'tour' in mt:
            cats['e2e'].append(t)
        elif 'system' in cl:
            cats['system'].append(t)
        elif 'integration' in cl or 'invoicing' in cl:
            cats['integration'].append(t)
        else:
            cats['unit'].append(t)

    # ── Sort each category by SHORT_LABELS order for logical reading ──
    label_order = {m: i for i, m in enumerate(SHORT_LABELS.keys())}
    for k in cats:
        cats[k].sort(key=lambda t: label_order.get(t['method'], 10000))
    return cats


# ─── HUMAN-READABLE TEST DESCRIPTIONS (column "Ce qu'il vérifie") ───
DESCRIPTIONS = {
    'test_default_values': "Les valeurs par défaut sont correctement appliquées à la création",
    'test_local_step1_customs_duties': "Étape 1 locale : application des droits de douane",
    'test_local_step2_conversion': "Étape 2 locale : conversion dans la devise du devis",
    'test_local_step3_fodec': "Étape 3 locale : application du FODEC",
    'test_local_step4_impot_douane': "Étape 4 locale : application de l'impôt de douane",
    'test_local_step5_avance_import': "Étape 5 locale : application de l'avance sur importation",
    'test_local_step6_margin_and_htva': "Étape 6 locale : marge et calcul du prix hors TVA",
    'test_local_montant_tva': "Calcul du montant de la TVA",
    'test_local_prix_ttc_final': "Calcul du prix TTC final",
    'test_local_marge_unitaire': "Calcul de la marge unitaire",
    'test_local_marge_total': "Calcul de la marge totale (unitaire × quantité)",
    'test_local_prix_total_ttc_quantity': "Prix total TTC = prix unitaire × quantité",
    'test_local_writes_price_unit': "Le prix calculé est écrit dans le champ prix unitaire Odoo",
    'test_foreign_step1_conversion': "Étape 1 étrangère : conversion du prix fournisseur",
    'test_foreign_step2_unit_sell_price': "Étape 2 étrangère : prix de vente unitaire",
    'test_foreign_unit_margin': "Marge unitaire étrangère",
    'test_foreign_total_margin': "Marge totale étrangère",
    'test_foreign_total_suggested_price': "Prix total suggéré",
    'test_foreign_writes_price_unit': "Le prix étranger est écrit dans le champ prix unitaire Odoo",
    'test_quantity_multiplier_local': "Changement de quantité met à jour les totaux (local)",
    'test_quantity_multiplier_foreign': "Changement de quantité met à jour les totaux (étranger)",
    'test_switching_calc_type_recomputes_both_chains': "Changement local/étranger recalcule les deux chaînes",
    'test_zero_supplier_price_gives_zero_chain': "Prix fournisseur à zéro : toute la chaîne donne zéro",
    'test_zero_conversion_rate_gives_zero_chain': "Taux de conversion à zéro : pas de division par zéro",
    'test_zero_quantity_gives_zero_total': "Quantité zéro : total à zéro",
    'test_margin_cap_at_100_percent_no_crash': "Marge à 100% : pas de division par zéro",
    'test_margin_above_100_percent_no_crash': "Marge > 100% : pas de crash",
    'test_negative_supplier_price_gives_negative_result': "Prix négatif : résultat négatif cohérent",
    'test_negative_quantity_gives_negative_total': "Quantité négative : total négatif cohérent",
    'test_foreign_negative_margin_no_crash': "Marge négative : pas de crash",
    'test_very_large_supplier_price_no_overflow': "Prix très élevé : pas de dépassement de capacité",
    'test_changing_supplier_price_updates_all_11_computed_fields': "Modification du prix recalcule tous les champs",
    'test_purchase_count_zero_initially': "Compteur BC fournisseur à zéro au départ",
    'test_purchase_count_computed_from_m2m': "Compteur BC augmente quand un BC est lié",
    'test_button_blocked_before_confirmation': "Le bouton BC refuse de fonctionner avant confirmation",
    'test_button_blocked_without_supplier': "Le bouton BC refuse de fonctionner sans fournisseur",
    'test_creates_purchase_order_with_correct_fields': "Le BC créé a le bon fournisseur, produit, quantité, prix",
    'test_po_origin_references_sale_order': "Le BC référence le numéro du devis (traçabilité)",
    'test_multiple_suppliers_create_separate_purchase_orders': "Deux fournisseurs → deux BC séparés",
    'test_same_supplier_groups_lines_into_one_po': "Même fournisseur → lignes groupées dans un seul BC",
    'test_purchase_ids_linked_back_to_sale_order': "Lien bidirectionnel BC → devis vérifié",
    'test_lines_without_supplier_are_excluded': "Lignes sans fournisseur ignorées sans erreur",
    'test_delivery_mode_field_exists_only_with_custom_invoice_xinxu':
        "Dépendance implicite avec custom_invoice_xinxu documentée",
    'test_full_cycle_local_devis_to_facture':
        "Cycle complet client local : devis → calcul → confirmation → BC → facture",
    'test_full_cycle_foreign_devis_to_facture':
        "Cycle complet client étranger : devis → calcul → confirmation → BC → facture",
    'test_full_cycle_multi_supplier_multi_line': "Cycle multi-fournisseur : 2 lignes → 2 BC → 1 facture",
    'test_cycle_blocked_if_po_attempted_before_confirmation':
        "Ordre des étapes respecté (BC interdit avant confirmation)",
    'test_01_xinxu_prix_calcul_tour': "Tour navigateur : parcours complet client local dans l'interface",
    'test_02_xinxu_prix_calcul_tour_foreign': "Tour navigateur : parcours complet client étranger dans l'interface",
}


# ─── SHORT BUSINESS LABELS (column "Test") — ordered logically ───
SHORT_LABELS = {
    'test_default_values': "Valeurs par défaut",
    'test_local_step1_customs_duties': "Droits de douane (local)",
    'test_local_step2_conversion': "Conversion devise (local)",
    'test_local_step3_fodec': "FODEC (local)",
    'test_local_step4_impot_douane': "Impôt de douane (local)",
    'test_local_step5_avance_import': "Avance sur importation",
    'test_local_step6_margin_and_htva': "Marge et prix HT",
    'test_local_montant_tva': "Montant de la TVA",
    'test_local_prix_ttc_final': "Prix TTC final",
    'test_local_marge_unitaire': "Marge unitaire",
    'test_local_marge_total': "Marge totale",
    'test_local_prix_total_ttc_quantity': "Prix total TTC",
    'test_local_writes_price_unit': "Écriture prix (local)",
    'test_foreign_step1_conversion': "Conversion fournisseur",
    'test_foreign_step2_unit_sell_price': "Prix vente unitaire",
    'test_foreign_unit_margin': "Marge unitaire (étr.)",
    'test_foreign_total_margin': "Marge totale (étr.)",
    'test_foreign_total_suggested_price': "Prix total suggéré",
    'test_foreign_writes_price_unit': "Écriture prix (étr.)",
    'test_quantity_multiplier_local': "Quantité (local)",
    'test_quantity_multiplier_foreign': "Quantité (étranger)",
    'test_switching_calc_type_recomputes_both_chains': "Bascule local/étranger",
    'test_zero_supplier_price_gives_zero_chain': "Prix fournisseur zéro",
    'test_zero_conversion_rate_gives_zero_chain': "Taux de change zéro",
    'test_zero_quantity_gives_zero_total': "Quantité zéro",
    'test_margin_cap_at_100_percent_no_crash': "Marge à 100%",
    'test_margin_above_100_percent_no_crash': "Marge > 100%",
    'test_negative_supplier_price_gives_negative_result': "Prix négatif",
    'test_negative_quantity_gives_negative_total': "Quantité négative",
    'test_foreign_negative_margin_no_crash': "Marge négative",
    'test_very_large_supplier_price_no_overflow': "Prix très élevé",
    'test_changing_supplier_price_updates_all_11_computed_fields': "Recalcul global",
    'test_purchase_count_zero_initially': "Compteur BC initial",
    'test_purchase_count_computed_from_m2m': "Compteur BC",
    'test_button_blocked_before_confirmation': "Blocage avant confirmation",
    'test_button_blocked_without_supplier': "Blocage sans fournisseur",
    'test_creates_purchase_order_with_correct_fields': "Champs du BC",
    'test_po_origin_references_sale_order': "Traçabilité BC",
    'test_multiple_suppliers_create_separate_purchase_orders': "Multi-fournisseurs",
    'test_same_supplier_groups_lines_into_one_po': "Groupement fournisseur",
    'test_purchase_ids_linked_back_to_sale_order': "Lien BC → devis",
    'test_lines_without_supplier_are_excluded': "Lignes sans fournisseur",
    'test_delivery_mode_field_exists_only_with_custom_invoice_xinxu': "Dépendance documentée",
    'test_full_cycle_local_devis_to_facture': "Cycle client local",
    'test_full_cycle_foreign_devis_to_facture': "Cycle client étranger",
    'test_full_cycle_multi_supplier_multi_line': "Cycle multi-fournisseur",
    'test_cycle_blocked_if_po_attempted_before_confirmation': "Ordre des étapes",
    'test_01_xinxu_prix_calcul_tour': "Tour client local",
    'test_02_xinxu_prix_calcul_tour_foreign': "Tour client étranger",
}


def get_short_label(method_name):
    """Return a short business-friendly label for the 'Test' column."""
    if method_name in SHORT_LABELS:
        return SHORT_LABELS[method_name]
    name = method_name.replace('test_', '').replace('_', ' ')
    return name[:28].capitalize()


def get_description(method_name):
    """Return human-readable description or generate one from the method name."""
    if method_name in DESCRIPTIONS:
        return DESCRIPTIONS[method_name]
    name = method_name.replace('test_', '').replace('_', ' ')
    return name.capitalize()


# ─── EXECUTIVE-SUMMARY HELPERS ───
def _kpi_cell(styles, val, label, color, bg, border):
    """Build a single KPI card (big number + small label)."""
    from reportlab.lib.enums import TA_CENTER as _TC
    vs = ParagraphStyle('kv_' + label, parent=styles['Normal'], fontSize=21,
                        fontName='Helvetica-Bold', textColor=color,
                        alignment=_TC, leading=25)
    ls = ParagraphStyle('kl_' + label, parent=styles['Normal'], fontSize=7.5,
                        textColor=GRAY, alignment=_TC, fontName='Helvetica')
    inner = Table([[Paragraph(f"<b>{val}</b>", vs)],
                   [Paragraph(label, ls)]], colWidths=[31*mm])
    inner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('BOX', (0, 0), (-1, -1), 1, border),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    return inner


def _bar_chart(cats, page_w):
    """Bar chart of test counts per level."""
    d = Drawing(page_w, 52*mm)
    order = ['unit', 'integration', 'system', 'e2e']
    names = {'unit': 'Unitaire', 'integration': 'Intégration',
             'system': 'Système', 'e2e': 'E2E'}
    cols = {'unit': BLUE, 'integration': BLUE2, 'system': BLUE3, 'e2e': BLUE4}
    counts = [(k, len(cats[k])) for k in order]
    max_n = max((c for _, c in counts), default=1) or 1
    bw, gap, max_h, x0 = 20*mm, 14*mm, 38*mm, 22*mm
    for i, (k, n) in enumerate(counts):
        x = x0 + i * (bw + gap)
        h = (n / max_n) * max_h
        d.add(Rect(x, 8*mm, bw, h, fillColor=cols[k], strokeColor=None))
        d.add(String(x + bw/2, 8*mm + h + 2, str(n), fontName='Helvetica-Bold',
                     fontSize=8, fillColor=BLUE, textAnchor='middle'))
        d.add(String(x + bw/2, 2*mm, names[k], fontName='Helvetica',
                     fontSize=7.5, fillColor=GRAY, textAnchor='middle'))
    return d


class CheckList(Flowable):
    """Coverage checklist drawn directly on the canvas — guarantees ✓ renders."""
    def __init__(self, items, col_width, row_h=13):
        super().__init__()
        self.items = items
        self.col_w = col_width
        self.row_h = row_h
        self.width = col_width * 2
        self.height = (len(items) // 2) * row_h + 2

    def draw(self):
        c = self.canv
        n_rows = len(self.items) // 2
        for r in range(n_rows):
            y = self.height - (r + 1) * self.row_h + 2
            for col in range(2):
                x = col * self.col_w
                idx = r * 2 + col
                if idx < len(self.items):
                    c.setFont('DejaVu', 9)
                    c.setFillColor(GREEN)
                    c.drawString(x + 4, y, '\u2713')
                    c.setFont('Helvetica', 9)
                    c.setFillColor(HexColor('#333333'))
                    c.drawString(x + 16, y, self.items[idx])
            if r < n_rows - 1:
                c.setStrokeColor(LIGHT)
                c.setLineWidth(0.3)
                c.line(0, y - 2, self.width, y - 2)


# ─── GENERATE PDF ───
def generate_pdf(results, output_path):
    _register_fonts()
    """Generate a professional PDF from parsed test results."""

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=18*mm, bottomMargin=18*mm,
        leftMargin=16*mm, rightMargin=16*mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    for name, conf in [
        ('MainTitle', dict(fontSize=20, textColor=BLUE, fontName='Helvetica-Bold',
                           alignment=TA_CENTER, spaceAfter=3*mm)),
        ('SubTitle', dict(fontSize=12, textColor=GRAY, fontName='Helvetica',
                          alignment=TA_CENTER, spaceAfter=6*mm)),
        ('Section', dict(fontSize=14, textColor=BLUE, fontName='Helvetica-Bold',
                         spaceBefore=6*mm, spaceAfter=3*mm)),
        ('SubSection', dict(fontSize=11, textColor=BLUE, fontName='Helvetica-Bold',
                            spaceBefore=4*mm, spaceAfter=2*mm)),
        ('Body', dict(fontSize=9.5, leading=13, fontName='Helvetica',
                      alignment=TA_JUSTIFY, spaceAfter=2.5*mm)),
        ('Cell', dict(fontSize=8.5, leading=11, fontName='Helvetica')),
        ('CellB', dict(fontSize=8.5, leading=11, fontName='Helvetica-Bold')),
        ('CellH', dict(fontSize=8.5, leading=11, fontName='Helvetica-Bold', textColor=white)),
        ('Big', dict(fontSize=40, textColor=GREEN, alignment=TA_CENTER,
                     fontName='Helvetica-Bold', leading=46, spaceAfter=3*mm)),
        ('BigLabel', dict(fontSize=11, textColor=BLUE, alignment=TA_CENTER,
                          fontName='Helvetica', leading=14, spaceAfter=5*mm)),
    ]:
        styles.add(ParagraphStyle(name, parent=styles['Normal'], **conf))

    story = []
    cats = categorize(results['tests'])
    total = results['summary'].get('total', len(results['tests']))
    failed = results['summary'].get('failed', 0)
    errors = results['summary'].get('errors', 0)
    passed = total - failed - errors

    # ── PAGE 1: COVER ──
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph("RAPPORT DE TESTS AUTOMATISÉS", styles['MainTitle']))
    story.append(HRFlowable(width="50%", thickness=2, color=BLUE, spaceAfter=4*mm))
    mod = results.get('module', 'xinxu_prix_calcul') or 'xinxu_prix_calcul'
    story.append(Paragraph(f"Module {mod}", styles['SubTitle']))
    story.append(Spacer(1, 4*mm))

    # Intro paragraph
    story.append(Paragraph(
        "Ce rapport présente les contrôles automatisés effectués sur le module de calcul des prix. "
        "Chaque test vérifie qu'une partie du système fonctionne correctement et signale "
        "immédiatement toute anomalie.",
        styles['Body']
    ))
    story.append(Spacer(1, 4*mm))

    # Info table
    info = [
        ["Environnement", f"Odoo {results.get('odoo_version', '18.0')}, Ubuntu 22.04 LTS, Chrome headless"],
        ["Date d'exécution", results.get('date', datetime.now().strftime('%Y-%m-%d'))],
        ["Durée totale", f"{results.get('duration', 0):.2f} secondes"],
        ["Requêtes SQL", f"{results.get('queries', 0):,}"],
    ]
    info_data = [
        [Paragraph(f"<b>{k}</b>", styles['Cell']), Paragraph(v, styles['Cell'])]
        for k, v in info
    ]
    info_tbl = Table(info_data, colWidths=[38*mm, 130*mm])
    info_tbl.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, GRAY),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 10*mm))

    # Big result — in a colored box for emphasis
    color = GREEN if failed == 0 and errors == 0 else RED
    box_bg = HexColor("#EAF7EF") if failed == 0 and errors == 0 else HexColor("#FDEDEC")
    box_border = GREEN if failed == 0 and errors == 0 else RED
    styles['Big'].textColor = color
    label = "tests réussis, 0 échec, 0 erreur" if failed == 0 and errors == 0 \
        else f"tests réussis, {failed} échec(s), {errors} erreur(s)"

    result_inner = [
        [Paragraph(f"{passed} / {total}", styles['Big'])],
        [Paragraph(label, styles['BigLabel'])],
    ]
    result_tbl = Table(result_inner, colWidths=[120*mm])
    result_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), box_bg),
        ('BOX', (0, 0), (-1, -1), 1.5, box_border),
        ('TOPPADDING', (0, 0), (0, 0), 6),
        ('BOTTOMPADDING', (0, 0), (0, 0), 0),
        ('TOPPADDING', (0, 1), (0, 1), 0),
        ('BOTTOMPADDING', (0, 1), (0, 1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    # Center the box on the page
    wrapper = Table([[result_tbl]], colWidths=[168*mm])
    wrapper.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(wrapper)
    story.append(Spacer(1, 8*mm))

    # Level summary
    story.append(Paragraph("Synthèse par niveau de test", styles['SubSection']))
    level_names = {
        'unit': ('Unitaire', 'Chaque formule testée individuellement avec des valeurs connues'),
        'integration': ('Intégration', 'Vérification des échanges de données entre modules'),
        'system': ('Système', 'Cycle commercial complet de A à Z sans raccourcis'),
        'e2e': ('E2E (navigateur)', 'Un vrai navigateur clique et navigue comme un utilisateur réel'),
    }
    sum_header = [
        Paragraph("<b>Niveau</b>", styles['CellH']),
        Paragraph("<b>Tests</b>", styles['CellH']),
        Paragraph("<b>Réussis</b>", styles['CellH']),
        Paragraph("<b>Ce que ça prouve</b>", styles['CellH']),
    ]
    sum_rows = [sum_header]
    for key in ['unit', 'integration', 'system', 'e2e']:
        tests_in_cat = cats[key]
        n = len(tests_in_cat)
        p = sum(1 for t in tests_in_cat if t['status'] == 'PASS')
        name, desc = level_names[key]
        status_color = GREEN if p == n else RED
        sum_rows.append([
            Paragraph(f"<b>{name}</b>", styles['Cell']),
            Paragraph(str(n), styles['Cell']),
            Paragraph(f"<font color='{status_color.hexval()}'>{p}/{n}</font>", styles['CellB']),
            Paragraph(desc, styles['Cell']),
        ])
    sum_tbl = Table(sum_rows, colWidths=[30*mm, 14*mm, 16*mm, 108*mm])
    sum_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BLUE),
        ('GRID', (0, 0), (-1, -1), 0.4, GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
    ]))
    story.append(sum_tbl)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════
    #  PAGE 2 — RÉSUMÉ EXÉCUTIF
    # ══════════════════════════════════════════════════════
    story.append(Paragraph("Résumé exécutif", styles['Section']))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=3*mm))
    story.append(Paragraph(
        "Le module <b>xinxu_prix_calcul</b> automatisé le calcul des prix de vente "
        "en intégrant l'ensemble des composantes tarifaires : droits de douane, FODEC, "
        "impôt de douane, avance sur importation, taux de change et marge commerciale. "
        "Ce calcul, auparavant réalisé manuellement, est désormais exécuté en temps réel "
        "au moment de la création d'un devis.",
        styles['Body']
    ))
    story.append(Paragraph(
        "Afin de garantir la fiabilité de ce module avant sa mise en production, une suite "
        f"de tests automatisés à quatre niveaux a été conçue et exécutée. Cette suite comprend "
        f"<b>{total} tests</b> couvrant les formules individuelles, les interactions entre "
        "modules, le cycle commercial complet et l'interface utilisateur via navigateur.",
        styles['Body']
    ))

    story.append(Paragraph("Résultat global", styles['SubSection']))
    ok = (failed == 0 and errors == 0)
    kc = GREEN if ok else RED
    kbg = GREEN_BG if ok else HexColor("#FDEDEC")
    rate = int(round(passed * 100.0 / total)) if total else 0
    kpi_row = [[
        _kpi_cell(styles, str(total), "Total tests", BLUE, LIGHT, BLUE),
        _kpi_cell(styles, str(passed), "Réussis", kc, kbg, kc),
        _kpi_cell(styles, str(failed), "Échecs", kc, kbg, kc),
        _kpi_cell(styles, str(errors), "Erreurs", kc, kbg, kc),
        _kpi_cell(styles, f"{rate}%", "Taux de réussite", kc, kbg, kc),
    ]]
    kpi_tbl = Table(kpi_row, colWidths=[33*mm]*5, hAlign='CENTER')
    kpi_tbl.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph("Répartition des tests par niveau", styles['SubSection']))
    story.append(_bar_chart(cats, 168*mm))
    story.append(Spacer(1, 3*mm))

    story.append(Paragraph("Couverture fonctionnelle", styles['SubSection']))
    cov_items = [
        "Formules de calcul des prix", "Calcul des marges commerciales",
        "Droits de douane et taxes", "Création de devis",
        "Génération des bons de commande", "Génération des factures",
        "Gestion multi-fournisseurs", "Workflows interface utilisateur",
    ]
    story.append(CheckList(cov_items, col_width=84*mm))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════
    #  PAGE 3 — IMPACT MÉTIER
    # ══════════════════════════════════════════════════════
    story.append(Paragraph("Impact métier", styles['Section']))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=3*mm))
    story.append(Paragraph(
        "Le tableau suivant présente, pour chaque fonctionnalité testée, "
        "la valeur concrète apportée à l'activité de l'entreprise.",
        styles['Body']
    ))
    impact_data = [
        ("Calcul des prix de vente",
         "Réduit le risque d'erreurs de devis et assure des marges cohérentes"),
        ("Conversion de devises",
         "Garantit l'exactitude des prix pour les clients locaux et étrangers"),
        ("Calcul de l'avance sur importation",
         "Intègre automatiquement une charge fiscale souvent oubliée dans les devis manuels"),
        ("Génération des bons de commande fournisseur",
         "Économise un travail manuel répétitif et évite les erreurs de saisie fournisseur"),
        ("Gestion multi-fournisseurs",
         "Prend en charge les approvisionnements complexes avec plusieurs fournisseurs"),
        ("Génération de la facture",
         "Garantit la cohérence entre le devis négocié et la facture émise"),
        ("Tests navigateur (tours E2E)",
         "Confirme que les employés peuvent utiliser la fonctionnalité sans assistance"),
        ("Lien bon de commande - devis d'origine",
         "Assure la traçabilité complète entre commande client et approvisionnement"),
    ]
    imp_hdr = [Paragraph("<b>Fonctionnalité testée</b>", styles['CellH']),
               Paragraph("<b>Bénéfice pour l'entreprise</b>", styles['CellH'])]
    imp_rows = [imp_hdr] + [
        [Paragraph(f, styles['CellB']), Paragraph(b, styles['Cell'])]
        for f, b in impact_data
    ]
    imp_tbl = Table(imp_rows, colWidths=[70*mm, 98*mm])
    imp_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BLUE),
        ('GRID', (0, 0), (-1, -1), 0.3, GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(imp_tbl)

    story.append(PageBreak())

    # ── DETAILED RESULTS ──
    story.append(Paragraph("Détail des tests", styles['Section']))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=3*mm))

    for key, title in [('unit', 'Tests unitaires'), ('integration', "Tests d'intégration"),
                       ('system', 'Tests de système'), ('e2e', 'Tests de bout en bout (E2E)')]:
        tests_in_cat = cats[key]
        if not tests_in_cat:
            continue

        n = len(tests_in_cat)
        p = sum(1 for t in tests_in_cat if t['status'] == 'PASS')
        story.append(Paragraph(f"{title} ({p}/{n})", styles['SubSection']))

        header = [
            Paragraph("<b>Test</b>", styles['CellH']),
            Paragraph("<b>Ce qu'il vérifie</b>", styles['CellH']),
            Paragraph("<b>Résultat</b>", styles['CellH']),
        ]
        rows = [header]
        for t in tests_in_cat:
            short = get_short_label(t['method'])
            desc = get_description(t['method'])
            if t['status'] == 'PASS':
                st = Paragraph("<font color='#27AE60'><b>PASS</b></font>", styles['Cell'])
            elif t['status'] == 'SKIP':
                st = Paragraph("<font color='#F39C12'><b>SKIP</b></font>", styles['Cell'])
            else:
                st = Paragraph("<font color='#E74C3C'><b>FAIL</b></font>", styles['Cell'])
            rows.append([
                Paragraph(short, styles['Cell']),
                Paragraph(desc, styles['Cell']),
                st,
            ])

        col1 = 42*mm if key != 'system' else 38*mm
        col2 = 168*mm - col1 - 16*mm
        tbl = Table(rows, colWidths=[col1, col2, 16*mm])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), BLUE),
            ('GRID', (0, 0), (-1, -1), 0.3, GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 4*mm))

    # ── TOURS DETAIL ──
    if results['tours']:
        story.append(PageBreak())
        story.append(Paragraph("Tours E2E — comment lancer le test dans le navigateur", styles['SubSection']))

        # Tour results (RÉUSSI / ECHOUE) — plain text, no colored background
        for tour in results['tours']:
            icon = "RÉUSSI" if tour['status'] == 'PASS' else "ECHOUE"
            icon_color = "#27AE60" if tour['status'] == 'PASS' else "#E74C3C"
            story.append(Paragraph(
                f"<font color='{icon_color}'><b>{icon}</b></font> — {tour['name']}",
                styles['Body']
            ))

        story.append(Spacer(1, 3*mm))
        story.append(Paragraph(
            "Pour reproduire ces tests visuellement dans le navigateur, suivre les étapes ci-dessous :",
            styles['Body']
        ))
        story.append(Spacer(1, 2*mm))

        # White text styles for dark box
        label_style = ParagraphStyle('DarkLabel', parent=styles['Normal'],
                                     fontSize=8.5, fontName='Helvetica-Bold',
                                     textColor=HexColor("#F0C040"), leading=12)
        text_style = ParagraphStyle('DarkText', parent=styles['Normal'],
                                    fontSize=8.5, fontName='Helvetica',
                                    textColor=HexColor("#ECF0F1"), leading=12)
        code_style = ParagraphStyle('DarkCode', parent=styles['Normal'],
                                    fontSize=8, fontName='Courier',
                                    textColor=HexColor("#2ECC71"), leading=12)

        steps = [
            ("Étape 1", "Aller dans Paramètres dans odoo, puis cliquer sur \"Activer le mode développeur (avec les assets test)\". La page se recharge automatiquement.", False),
            ("Étape 2", "Naviguer vers Ventes > Commandes > Devis, puis basculer en vue liste (icône liste en haut à droite).", False),
            ("Étape 3", "Appuyer sur F12 pour ouvrir la console développeur, puis cliquer sur l'onglet Console.", False),
            ("Étape 4 — Tour client local", "Coller la commande suivante et appuyer sur Entrée :", False),
            ("", "odoo.startTour('xinxu_prix_calcul_tour', {debug: false, stepDelay: 1500})", True),
            ("Étape 5 — Observer", "Le navigateur exécutée automatiquement les étapes : création du devis, saisie du client, calcul du prix TTC, confirmation. Le test se termine quand \"tour succeeded\" apparaît dans la console.", False),
            ("Étape 6 — Tour client etranger", "Répéter les étapes 2 à 4 avec la commande :", False),
            ("", "odoo.startTour('xinxu_prix_calcul_tour_foreign', {debug: false, stepDelay: 1500})", True),
            ("Note", "Chaque tour crée un vrai devis dans la base de production. Penser à le supprimer après la démonstration.", False),
        ]

        step_data = []
        for label, text, is_code in steps:
            if label == "" and is_code:
                step_data.append([
                    Paragraph("", text_style),
                    Paragraph(text, code_style),
                ])
            else:
                step_data.append([
                    Paragraph(label, label_style) if label else Paragraph("", text_style),
                    Paragraph(text, text_style),
                ])

        step_tbl = Table(step_data, colWidths=[42*mm, 121*mm])
        step_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), DARK),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -2), 0.3, HexColor("#4A4A6A")),
            ('BOX', (0, 0), (-1, -1), 1, HexColor("#4A4A6A")),
        ]))
        story.append(step_tbl)
        story.append(Spacer(1, 8*mm))

    # ── HOW TO REPRODUCE (same page as E2E) ──
    story.append(Paragraph("Reproductibilité : relancer la suite de tests à tout moment", styles['Section']))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=3*mm))

    story.append(Paragraph(
        "Ces tests sont reproductibles à tout moment. La commande ci-dessous "
        "exécute l'intégralité de la suite et génère ce rapport :",
        styles['Body']
    ))

    cmd = "/opt/odoo/run_xinxu_tests.sh"
    cmd_html = cmd.replace(' ', '&nbsp;')
    cmd_data = [[Paragraph(
        f"<font face='Courier' size='8' color='#ECF0F1'>{cmd_html}</font>",
        styles['Cell']
    )]]
    cmd_tbl = Table(cmd_data, colWidths=[168*mm])
    cmd_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK),
        ('BOX', (0, 0), (-1, -1), 1, GRAY),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(cmd_tbl)

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        f"<i>Rapport génère automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')} "
        f"a partir de la sortie terminale des tests Odoo.</i>",
        ParagraphStyle('footer', parent=styles['Normal'], fontSize=8,
                       textColor=GRAY, alignment=TA_CENTER)
    ))

    # ══════════════════════════════════════════════════════
    #  FINAL PAGE — CONCLUSION
    # ══════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Conclusion", styles['Section']))
    story.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=3*mm))

    ok = (failed == 0 and errors == 0)
    n_unit = len(cats['unit'])
    n_int = len(cats['integration'])
    n_sys = len(cats['system'])
    n_e2e = len(cats['e2e'])

    if ok:
        c_box, c_bg = GREEN, GREEN_BG
        c_title = ("<font color='#27AE60'><b>✓  Validation complète - "
                   f"{passed}/{total} tests réussis</b></font>")
        c_p1 = (f"La suite de tests automatisés du module <b>{mod}</b> a été exécutée dans "
                f"son intégralité et produit un résultat de <b>{passed} tests réussis sur "
                f"{total}</b>, sans aucun échec ni erreur. Ce résultat confirmé que le module "
                "est prêt pour la mise en production.")
    else:
        c_box, c_bg = RED, HexColor("#FDEDEC")
        c_title = ("<font color='#E74C3C'><b>✗  Anomalies détectées - "
                   f"{passed}/{total} tests réussis, {failed} échec(s), {errors} erreur(s)</b></font>")
        c_p1 = (f"La suite de tests automatisés du module <b>{mod}</b> a été exécutée et "
                f"produit <b>{failed} échec(s)</b> et <b>{errors} erreur(s)</b> sur un total de "
                f"{total} tests. Ces anomalies doivent être corrigées avant la mise en production. "
                "Le détail des tests en échec figure dans les tableaux précédents.")

    cb = ParagraphStyle('ConcBody', parent=styles['Normal'],
                        fontSize=9, leading=14, fontName='Helvetica',
                        alignment=TA_JUSTIFY, spaceAfter=3*mm)
    ct = ParagraphStyle('ConcTitle', parent=styles['Normal'],
                        fontSize=12, fontName='Helvetica-Bold', spaceAfter=4*mm)

    c_p2 = (f"Les {n_unit} tests unitaires garantissent l'exactitude de chaque formule de "
            f"calcul individuellement. Les {n_int} tests d'intégration confirment la cohérence "
            "des échanges de données entre le module de calcul des prix, le module des achats "
            f"et le module de facturation. Les {n_sys} tests système valident le cycle commercial "
            f"complet, du devis jusqu'à la facture, sans raccourcis. Enfin, les {n_e2e} tours "
            "navigateur prouvent que l'interface utilisateur fonctionne correctement pour les "
            "deux types de clients : locaux et étrangers.")
    c_p3 = ("Cette suite peut être rejouée à tout moment, notamment après une mise à jour "
            "d'Odoo ou une modification du module, pour détecter immédiatement toute régression.")

    conc_inner = Table([
        [Paragraph(c_title, ct)],
        [Paragraph(c_p1, cb)],
        [Paragraph(c_p2, cb)],
        [Paragraph(c_p3, cb)],
    ], colWidths=[152*mm])
    conc_inner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), c_bg),
        ('BOX', (0, 0), (-1, -1), 1.5, c_box),
        ('TOPPADDING', (0, 0), (0, 0), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
    ]))
    conc_wrap = Table([[conc_inner]], colWidths=[168*mm])
    conc_wrap.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(conc_wrap)

    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(
        f"<i>Rapport généré automatiquement le {datetime.now().strftime('%d/%m/%Y à %H:%M')} "
        f"à partir de la sortie terminale des tests Odoo.</i>",
        ParagraphStyle('footer_conc', parent=styles['Normal'], fontSize=8,
                       textColor=GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)
    return output_path


# ─── MAIN ───
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 generate_test_report.py <chemin_vers_log>")
        print("Exemple: python3 generate_test_report.py /tmp/test_results.log")
        sys.exit(1)

    log_path = sys.argv[1]
    if not os.path.exists(log_path):
        print(f"Fichier introuvable : {log_path}")
        sys.exit(1)

    print(f"Analyse du log : {log_path}")
    results = parse_log(log_path)

    n_tests = len(results['tests'])
    n_pass = sum(1 for t in results['tests'] if t['status'] == 'PASS')
    n_fail = sum(1 for t in results['tests'] if t['status'] == 'FAIL')
    n_skip = sum(1 for t in results['tests'] if t['status'] == 'SKIP')
    print(f"Tests trouves : {n_tests} (PASS: {n_pass}, FAIL: {n_fail}, SKIP: {n_skip})")
    print(f"Tours E2E : {len(results['tours'])}")

    # ── Output PDF into the tests/report/ folder ──
    from datetime import datetime as _dt
    DEFAULT_REPORT_DIR = '/opt/odoo/custom_addons/xinxu_prix_calcul/tests/report'
    if len(sys.argv) >= 3:
        report_dir = sys.argv[2]
    elif os.path.isdir(os.path.dirname(DEFAULT_REPORT_DIR)):
        report_dir = DEFAULT_REPORT_DIR
    else:
        report_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'report'
        )
    os.makedirs(report_dir, exist_ok=True)
    stamp = _dt.now().strftime('%Y%m%d_%H%M%S')
    output = os.path.join(report_dir, f'rapport_tests_{stamp}.pdf')

    print(f"Génération du PDF : {output}")
    generate_pdf(results, output)
    print(f"Rapport génère avec succes : {output}")
    print(f"Dossier : {report_dir}")