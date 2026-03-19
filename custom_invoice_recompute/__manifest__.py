{
    'name': 'Custom Invoice Recompute',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Ajoute un bouton pour recalculer les lignes de facture après changement de devise',
    'description': """
        Ce module ajoute un bouton "Recalculer les lignes" sur les factures en brouillon.
        Utile pour forcer le recalcul des montants après un changement de devise.
    """,
    'author': 'Votre Nom',
    'website': 'https://votresite.com',
    'depends': ['account'],
    'data': [
        'views/account_move_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
