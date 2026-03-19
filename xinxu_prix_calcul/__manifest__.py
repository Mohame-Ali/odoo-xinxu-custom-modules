# -*- coding: utf-8 -*-
{
    'name': 'XINXU — Tableau de Calcul Prix',
    'version': '18.0.2.0.0',
    'summary': 'Calcul automatique du prix de vente sur les devis (Local TND / Étranger EUR) + création BC fournisseur',
    'description': """
        Flux réel XINXU :
        ─────────────────
        DDP fournisseurs (Tableau Comparatif)
              ↓
        Devis client  ← Tableau de Calcul ici
              ↓
        Manager approuve
              ↓
        Proforma envoyée au client
              ↓
        Client accepte → Commande de vente
              ↓
        Bouton "Créer le BC fournisseur" → purchase.order

        Deux tableaux de calcul sur sale.order.line :
        • Client Local (TND)    : chaîne douanière complète (6 étapes)
        • Client Étranger (EUR) : conversion + marge (2 étapes)
    """,
    'author': 'XINXU COMPANY',
    'category': 'Sales',
    'license': 'LGPL-3',
    'depends': ['sale', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
