{
    'name': 'Custom Stock Picking Sequence',
    'version': '18.0.1.0.0',
    'summary': 'Personnalise la numérotation des bons de livraison',
    'description': """
        Permet de définir une séquence personnalisée par type d'opération de stock.
        Exemple : BL001/2026 pour les livraisons sortantes.
    """,
    'author': 'Votre Nom',
    'category': 'Stock',
    'depends': ['stock'],
    'data': [
        'views/stock_picking_type_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}