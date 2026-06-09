# -*- coding: utf-8 -*-
from odoo import api, models, fields
import logging

log_file = '/var/log/odoo/custom_invoice_recompute.log'
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger = logging.getLogger('custom_invoice_recompute')
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)


class AccountMove(models.Model):
    _inherit = 'account.move'

    original_currency_id = fields.Many2one(
        'res.currency',
        string="Devise d'origine",
        help="Devise dans laquelle les prix des lignes sont actuellement exprimés.",
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if not move.original_currency_id:
                move.original_currency_id = move.currency_id
        return moves

    def write(self, vals):
        # Capture the OLD currency before it gets overwritten
        if vals.get('currency_id'):
            for move in self:
                if (
                    not move.original_currency_id
                    and move.currency_id
                    and move.currency_id.id != vals['currency_id']
                ):
                    super(AccountMove, move).write(
                        {'original_currency_id': move.currency_id.id}
                    )
                    logger.info(
                        "Move %s: stored original currency %s before change",
                        move.name, move.currency_id.name,
                    )
        return super().write(vals)

    def action_recompute_lines(self):
        """
        Convertit les prix existants des lignes depuis la devise d'origine
        vers la devise actuelle de la facture. Le prix négocié est conservé.
        """
        logger.info("=== action_recompute_lines CALLED ===")

        for move in self:
            if move.state != 'draft':
                logger.warning("Move %s not draft, skipping", move.name)
                continue

            source_currency = move.original_currency_id or move.currency_id
            target_currency = move.currency_id
            date = move.invoice_date or fields.Date.today()

            logger.info("Move %s: source=%s target=%s",
                        move.name, source_currency.name, target_currency.name)

            if source_currency == target_currency:
                logger.info("Same currency, nothing to convert")
                continue

            for line in move.invoice_line_ids:
                if not line.price_unit:
                    continue
                old_price = line.price_unit
                converted = source_currency._convert(
                    from_amount=old_price,
                    to_currency=target_currency,
                    company=move.company_id,
                    date=date,
                )
                line.write({'price_unit': converted})
                logger.info("Line %s: %s %s -> %s %s",
                            line.id, old_price, source_currency.name,
                            converted, target_currency.name)

            # Prices are now expressed in the target currency
            move.original_currency_id = target_currency

        logger.info("=== action_recompute_lines FINISHED ===")
        return {'type': 'ir.actions.client', 'tag': 'reload'}