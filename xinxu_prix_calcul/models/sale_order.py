# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    xinxu_calc_type = fields.Selection(
        selection=[
            ('local',   'Local Customer'),
            ('foreign', 'Foreign Customer'),
        ],
        string='Calculation Type',
        default='local',
        required=True,
        help="Determines the calculation table used on the lines:\n"
             "- Local   -> conversion + customs chain (6 steps)\n"
             "- Foreign -> conversion + margin (2 steps)",
    )

    xinxu_delivery_mode = fields.Char(
        string='Delivery Mode',
        default='Rendu usine',
        help="Delivery mode.",
    )

    xinxu_purchase_ids = fields.Many2many(
        comodel_name='purchase.order',
        relation='xinxu_sale_purchase_rel',
        column1='sale_id',
        column2='purchase_id',
        string='Supplier Purchase Orders',
        copy=False,
    )

    xinxu_purchase_count = fields.Integer(
        compute='_compute_xinxu_purchase_count',
        string='Supplier PO Count',
    )

    @api.depends('xinxu_purchase_ids')
    def _compute_xinxu_purchase_count(self):
        for order in self:
            order.xinxu_purchase_count = len(order.xinxu_purchase_ids)

    def action_xinxu_create_purchase_order(self):
        """Create a purchase.order from the confirmed sale order."""
        self.ensure_one()

        if self.state not in ('sale', 'done'):
            raise UserError(_(
                "The supplier purchase order can only be created "
                "after the customer has confirmed the quotation."
            ))

        lines_with_supplier = self.order_line.filtered(
            lambda l: l.x_supplier_id and not l.display_type
        )

        if not lines_with_supplier:
            raise UserError(_(
                "No line has a supplier set.\n"
                "Please fill in the 'Supplier' field on each line "
                "in the Calculation Table tab."
            ))

        suppliers = lines_with_supplier.mapped('x_supplier_id')
        created_pos = self.env['purchase.order']

        for supplier in suppliers:
            supplier_lines = lines_with_supplier.filtered(
                lambda l: l.x_supplier_id == supplier
            )

            po_lines = []
            for sl in supplier_lines:
                po_lines.append((0, 0, {
                    'product_id':   sl.product_id.id,
                    'name':         sl.name,
                    'product_qty':  sl.product_uom_qty,
                    'product_uom':  sl.product_uom.id,
                    'price_unit':   sl.x_supplier_price,
                    'date_planned': fields.Datetime.now(),
                }))

            po = self.env['purchase.order'].create({
                'partner_id': supplier.id,
                'origin':     self.name,
                'order_line': po_lines,
                'notes':      _(
                    "Purchase order created automatically from quotation %s"
                ) % self.name,
            })
            created_pos |= po

        self.xinxu_purchase_ids |= created_pos

        if len(created_pos) == 1:
            return {
                'type':      'ir.actions.act_window',
                'res_model': 'purchase.order',
                'res_id':    created_pos.id,
                'view_mode': 'form',
                'target':    'current',
            }
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain':    [('id', 'in', created_pos.ids)],
            'target':    'current',
        }

    def action_view_xinxu_purchases(self):
        """Smart button: view linked supplier purchase orders."""
        self.ensure_one()
        return {
            'type':      'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain':    [('id', 'in', self.xinxu_purchase_ids.ids)],
            'target':    'current',
        }

    def _prepare_invoice(self):
        """Override to copy the delivery mode from the sale order to the invoice."""
        invoice_vals = super()._prepare_invoice()
        invoice_vals['xinxu_delivery_mode'] = self.xinxu_delivery_mode
        return invoice_vals
