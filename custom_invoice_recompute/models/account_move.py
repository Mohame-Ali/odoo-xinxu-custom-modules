# -*- coding: utf-8 -*-
from odoo import models, api, fields
import logging

# Configuration du logger
log_file = '/var/log/odoo/custom_invoice_recompute.log'
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger = logging.getLogger('custom_invoice_recompute')
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_recompute_lines(self):
        """
        Recalcule les lignes de facture après changement de devise.
        Pour chaque ligne avec produit, met à jour le prix unitaire en convertissant
        le prix du produit (en devise société) vers la devise de la facture.
        """
        logger.info("=== action_recompute_lines CALLED ===")

        for move in self:
            logger.info("Processing move: %s (ID: %s, State: %s, Currency: %s)",
                        move.name, move.id, move.state, move.currency_id.name)

            if move.state != 'draft':
                logger.warning("Move %s is not in draft state, skipping", move.name)
                continue

            line_count = len(move.invoice_line_ids)
            logger.info("Move has %s invoice lines", line_count)

            # Récupérer la devise de la société et la devise de la facture
            company_currency = move.company_id.currency_id
            invoice_currency = move.currency_id
            logger.info("Company currency: %s, Invoice currency: %s", company_currency.name, invoice_currency.name)

            # Pour chaque ligne
            for idx, line in enumerate(move.invoice_line_ids):
                logger.info("--- Processing line %s/%s ---", idx+1, line_count)
                logger.info("Line ID: %s", line.id)
                logger.info("Product: %s", line.product_id.name or "No product")
                logger.info("Current price_unit: %s %s", line.price_unit, invoice_currency.name)
                logger.info("Quantity: %s", line.quantity)

                if line.product_id:
                    # Récupérer le prix de vente du produit (en devise société)
                    product_price = line.product_id.list_price
                    logger.info("Product list price (in company currency): %s %s", product_price, company_currency.name)

                    # Convertir ce prix dans la devise de la facture
                    try:
                        converted_price = company_currency._convert(
                            from_amount=product_price,
                            to_currency=invoice_currency,
                            company=move.company_id,
                            date=move.invoice_date or fields.Date.today(),
                        )
                        logger.info("Converted price: %s %s", converted_price, invoice_currency.name)

                        # Mettre à jour le prix unitaire de la ligne
                        line.write({'price_unit': converted_price})
                        logger.info("✓ price_unit updated to %s", converted_price)

                    except Exception as e:
                        logger.error("Error converting price: %s", str(e), exc_info=True)
                else:
                    # Ligne sans produit : on ne change pas le prix
                    logger.info("Line has no product, skipping price conversion")

                # Après modification, on peut forcer un recalcul des sous-totaux (optionnel)
                logger.info("Subtotal after update: %s", line.price_subtotal)

            # Recalculer les totaux de la facture
            logger.info("Recomputing move totals...")
            try:
                move._compute_amount()
                logger.info("✓ _compute_amount() executed")
                logger.info("New amount total (in invoice currency): %s", move.amount_total)
                logger.info("New amount total (in company currency): %s", move.amount_total_signed)
            except Exception as e:
                logger.error("Error computing totals: %s", str(e), exc_info=True)

        logger.info("=== action_recompute_lines FINISHED ===")

        # Rafraîchir la vue
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
