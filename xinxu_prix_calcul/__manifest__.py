# -*- coding: utf-8 -*-
{
    'name': 'XINXU — Tableau de Calcul Prix',
    'version': '18.0.2.0.0',
    'summary': 'Calcul automatique du prix de vente sur les devis (Local TND / Étranger EUR) + création BC fournisseur',
    'description': """
        Flux réel XINXU :
        DDP fournisseurs (Tableau Comparatif)
              vers
        Devis client  (Tableau de Calcul ici)
              vers
        Manager approuve
              vers
        Proforma envoyée au client
              vers
        Client accepte vers Commande de vente
              vers
        Bouton "Créer le BC fournisseur" vers purchase.order

        Deux tableaux de calcul sur sale.order.line :
        Client Local (TND) : chaîne douanière complète (6 étapes)
        Client Étranger (EUR) : conversion + marge (2 étapes)
    """,
    'author': 'XINXU COMPANY',
    'category': 'Sales',
    'license': 'LGPL-3',
    'depends': ['sale', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_view.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'xinxu_prix_calcul/static/tests/tours/xinxu_prix_calcul_tour.js',
            'xinxu_prix_calcul/static/tests/tours/xinxu_prix_calcul_tour_foreign.js',
        ],
    },    
    'installable': True,
    'application': False,
    'auto_install': False,
}
