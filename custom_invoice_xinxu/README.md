# custom_invoice_xinxu — Odoo 18 Custom Invoice Module

Reproduces the **XINXU COMPANYY** paper invoice layout inside Odoo 18 as a
fully dynamic QWeb / PDF report.

---

## 📁 Module Structure

```
custom_invoice_xinxu/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── res_company.py      ← custom fields: RIB, Banque, Agence
│   └── account_move.py     ← custom fields: Delivery Mode, Origin of Goods
├── views/
│   ├── report_invoice.xml  ← QWeb report template (main file)
│   └── res_company_view.xml← Form view extensions
└── static/src/scss/
    └── invoice_xinxu.scss  ← CSS (loaded at PDF render time)
```

---

## 🚀 Installation

1. **Copy the module** into your Odoo addons path:
   ```bash
   cp -r custom_invoice_xinxu /path/to/odoo/addons/
   ```

2. **Restart the Odoo service**:
   ```bash
   sudo systemctl restart odoo
   # or
   python odoo-bin -c odoo.conf --dev=all
   ```

3. **Activate developer mode** in Odoo:
   `Settings → General Settings → Developer Tools → Activate developer mode`

4. **Update the apps list**:
   `Apps → Update Apps List`

5. **Install the module**:
   Search for **"XINXU Invoice"** and click *Install*.

---

## ⚙️ Configuration

### A — Company header fields

Go to **Settings → Companies → [your company]** and fill in the new
**XINXU Invoice Info** section:

| Field | Example value |
|-------|---------------|
| RIB | `04 305 056 0074613696 86` |
| Banque | `Attijari Banque` |
| Agence bancaire | `Bou Argoub` |

The standard Odoo fields are used automatically:

| Odoo field | Shown as |
|------------|----------|
| `company.name` | Large company name (top-left) |
| `company.street` / `city` / `country` | Address line |
| `company.vat` | MF number |
| `company.phone` | Tel |
| `company.email` | Email |
| `company.logo` | Logo image (top-right) |

### B — Per-invoice export conditions

On each invoice, open the **Other Info** tab and fill in:

| Field | Default | Description |
|-------|---------|-------------|
| Delivery Mode | `CPT ALGERIA` | Footer line 2 |
| Origin of Goods | `TUNISIA` | Footer line 4 |

The **Payment Terms** footer line is pulled automatically from
`invoice.invoice_payment_term_id.name`.

---

## 🖨️ Printing the invoice

### Option 1 — As a new report action
The module registers a new print action called **"XINXU Invoice"** that
appears in the *Print* dropdown on every customer invoice.

### Option 2 — Replace the default invoice
If you want the XINXU template to replace the *standard* Odoo invoice
(i.e., appear when clicking the default *Print* button), add this to
`views/report_invoice.xml` **after** the `<template>` blocks:

```xml
<!-- Make XINXU template the default invoice report -->
<record id="account.action_report_account_invoice" model="ir.actions.report">
    <field name="report_name">
        custom_invoice_xinxu.report_invoice_xinxu_document
    </field>
</record>
```

---

## 🎨 Customising the look

### Colours / fonts
Edit `static/src/scss/invoice_xinxu.scss`.
All PDF-compatible properties are supported (wkhtmltopdf uses CSS 2.1 + parts of CSS 3).

### Column widths
In `invoice_xinxu.scss`, locate the **Column widths** section and adjust
the percentage values for `.xinxu-col-*` classes.

### Blank filler rows
In `report_invoice.xml`, find `range(max(0, 3 - filled_rows))` and change
`3` to the minimum number of rows you want to show.

### "Total says" (amount in words)
The template calls `o.currency_id.amount_to_text(o.amount_total)`.
This method is available in Odoo 16+. If it is missing in your build, replace
it with a custom compute field on `account.move`.

---

## 🔧 Troubleshooting

| Symptom | Fix |
|---------|-----|
| Logo not visible | Ensure a logo is uploaded in Settings → Companies |
| `xinxu_rib` field missing | Confirm the module is **installed** (not just updated) |
| PDF has no CSS | Check that `web.report_assets_common` includes the SCSS asset |
| `amount_to_text` error | Install `account_check_printing` or add a compute field |
| `xinxu_delivery_mode` error | The `account_move.py` model extension was not loaded — restart Odoo |

---

## 📄 Licence

LGPL-3  © XINXU COMPANYY
