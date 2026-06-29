# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from datetime import date, timedelta
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_range(self, filter_key, custom_start=None, custom_end=None):
        today = date.today()

        if filter_key == 'this_week':
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            return start, min(end, today)

        elif filter_key == 'this_month':
            return today.replace(day=1), today

        elif filter_key == 'this_year':
            return today.replace(month=1, day=1), today

        elif filter_key == 'custom' and custom_start and custom_end:
            if custom_end < custom_start:
                raise UserError(_("Please select a valid range"))
            return custom_start, custom_end

        return None, None

    def _build_global_domain(self, base_domain, filters, date_field="date_order"):
        global_filter = filters.get("global_filter", "this_week")
        if global_filter == "select_period":
            global_filter = "this_week"

        if global_filter == "custom":
            custom_range = filters.get("custom_range", {})
            custom_start = custom_range.get("from")
            custom_end = custom_range.get("to")
        else:
            custom_start = None
            custom_end = None

        from_date, to_date = self._get_range(global_filter, custom_start, custom_end)

        domain = base_domain.copy()
        if from_date:
            domain.append((date_field, '>=', from_date))
        if to_date:
            domain.append((date_field, '<=', to_date))
        return domain

    @api.model
    def get_tile_domain(self, base_domain, filters):
        return self._build_global_domain(base_domain, filters)

    def _aggregate_amounts_by(self, model, domain, dimension, limit,
                              company_currency, conv_date, amount_field='amount_total'):
        """Regroupe les enregistrements de `model` par `dimension` ET par devise,
        convertit chaque montant dans la devise de la societe avant agregation,
        afin que les chiffres multi-devises soient comparables. Renvoie les
        `limit` premieres entrees triees sur le montant converti, chacune avec
        un `amount` numerique (pour les graphiques) et un `amount_display`
        formate (pour les tableaux)."""
        groups = self.env[model].read_group(
            domain, [amount_field], [dimension, 'currency_id'], lazy=False,
        )
        totals = {}
        for g in groups:
            dim = g.get(dimension)
            if not dim:
                continue
            rec_id, rec_name = dim[0], dim[1]
            amount = g.get(amount_field) or 0.0
            currency = g.get('currency_id')
            if currency and currency[0] != company_currency.id:
                amount = self.env['res.currency'].browse(currency[0])._convert(
                    amount, company_currency, self.env.company, conv_date)
            entry = totals.setdefault(rec_id, {'id': rec_id, 'name': rec_name, 'amount': 0.0})
            entry['amount'] += amount
        rows = sorted(totals.values(), key=lambda r: r['amount'], reverse=True)[:limit]
        for r in rows:
            r['amount_display'] = company_currency.format(r['amount'])
        return rows

    @api.model
    def get_sales_dashboard_data(self, filters=None):
        filters = filters or {}
        limit = int(filters.get("limit", 10))
        company_currency = self.env.company.currency_id
        conv_date = fields.Date.today()

        def get_filter_key(specific_filter_key):
            global_filter = filters.get("global_filter", "this_week")
            if global_filter == "custom":
                return "custom"
            elif global_filter == "select_period":
                return filters.get(specific_filter_key, "this_week")
            else:
                return global_filter

        def build_domain(base_domain, specific_filter_key, date_field="date_order"):
            filter_key = get_filter_key(specific_filter_key)

            if filter_key == "custom":
                custom_range = filters.get("custom_range", {})
                custom_start = custom_range.get("from")
                custom_end = custom_range.get("to")
            else:
                custom_start = None
                custom_end = None

            from_date, to_date = self._get_range(filter_key, custom_start, custom_end)

            domain = base_domain.copy()
            if from_date:
                domain.append((date_field, '>=', from_date))
            if to_date:
                domain.append((date_field, '<=', to_date))
            return domain

        team_domain = build_domain([('state', 'in', ['sale', 'done'])], "team_filter")
        teams = self._aggregate_amounts_by('sale.order', team_domain, 'team_id',
                                           limit, company_currency, conv_date)

        person_domain = build_domain([('state', 'in', ['sale', 'done'])], "person_filter")
        persons = self._aggregate_amounts_by('sale.order', person_domain, 'user_id',
                                             limit, company_currency, conv_date)

        customer_domain = build_domain([('state', 'in', ['sale', 'done'])], "customer_filter")
        customers = self._aggregate_amounts_by('sale.order', customer_domain, 'partner_id',
                                               limit, company_currency, conv_date)

        product_domain = build_domain([('order_id.state', 'in', ['sale', 'done'])],
                                      "product_filter", "order_id.date_order")
        if filters.get("product_category_id"):
            product_domain.append(('product_id.categ_id', '=', filters["product_category_id"]))
        top_products_grouped = self.env['sale.order.line'].read_group(
            product_domain, ['product_uom_qty'], ['product_id'],
            limit=limit, orderby='product_uom_qty desc'
        )
        top_products = [
            {'id': rec['product_id'][0], 'name': rec['product_id'][1], 'qty': rec['product_uom_qty']}
            for rec in top_products_grouped if rec['product_id']
        ]

        low_product_domain = build_domain([('order_id.state', 'in', ['sale', 'done'])],
                                          "low_product_filter", "order_id.date_order")
        if filters.get("low_product_category_id"):
            low_product_domain.append(('product_id.categ_id', '=', filters["low_product_category_id"]))
        low_products_grouped = self.env['sale.order.line'].read_group(
            low_product_domain, ['product_uom_qty'], ['product_id'],
            limit=limit, orderby='product_uom_qty asc'
        )
        low_products = [
            {'id': rec['product_id'][0], 'name': rec['product_id'][1], 'qty': rec['product_uom_qty']}
            for rec in low_products_grouped if rec['product_id']
        ]

        order_domain = build_domain([], "order_filter")
        order_status_grouped = self.read_group(order_domain, ['id'], ['state'])
        ORDER_STATUS_LABELS = {
            'draft': _('Quotation'),
            'sent': _('Quotation Sent'),
            'sale': _('Sales Order'),
            'done': _('Locked'),
            'cancel': _('Cancelled'),
        }
        order_status = [
            {'status': ORDER_STATUS_LABELS.get(rec['state'], rec['state'].capitalize()),
             'count': rec['state_count']}
            for rec in order_status_grouped
        ]

        invoice_domain = build_domain([('move_type', '=', 'out_invoice')], "invoice_filter", "invoice_date")
        invoice_status_grouped = self.env['account.move'].read_group(invoice_domain, ['id'], ['state'])
        INVOICE_STATUS_LABELS = {
            'draft': _('Draft'),
            'posted': _('Posted'),
            'cancel': _('Cancelled'),
        }
        invoice_status = [
            {'status': INVOICE_STATUS_LABELS.get(rec['state'], rec['state'].capitalize()),
             'count': rec['state_count']}
            for rec in invoice_status_grouped
        ]

        overdue_customers_domain = build_domain([
            ('move_type', '=', 'out_invoice'),
            ('payment_state', '!=', 'paid'),
            ('invoice_date_due', '<', fields.Date.today())
        ], "overdue_filter", "invoice_date")
        overdue_customers = self._aggregate_amounts_by(
            'account.move', overdue_customers_domain, 'partner_id',
            limit, company_currency, conv_date)

        categories = self.env['product.category'].search([])
        product_categories = [{'id': c.id, 'name': c.display_name} for c in categories]

        sale_orders_domain = build_domain([('state', 'in', ['sale', 'done'])], "order_tile_filter")
        sale_orders = self.search_count(sale_orders_domain)

        quotations_domain = build_domain([('state', 'in', ['draft', 'sent'])], "quotation_tile_filter")
        quotations = self.search_count(quotations_domain)

        orders_to_invoice_domain = build_domain([('invoice_status', '=', 'to invoice')], "to_invoice_tile_filter")
        orders_to_invoice = self.search_count(orders_to_invoice_domain)

        orders_fully_invoiced_domain = build_domain([('invoice_status', '=', 'invoiced')], "invoiced_tile_filter")
        orders_fully_invoiced = self.search_count(orders_fully_invoiced_domain)

        conversion_rate = round(
            (sale_orders / (quotations + sale_orders) * 100) if (quotations + sale_orders) > 0 else 0)

        SaleOrder = self.env['sale.order']
        company_currency = self.env.company.currency_id
        today = fields.Date.today()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        def _get_total(start_date):
            groups = SaleOrder.read_group(
                [('state', '=', 'sale'), ('date_order', '>=', start_date)],
                ['amount_total:sum'],
                ['currency_id']
            )
            total = 0.0
            for g in groups:
                if g['currency_id']:
                    currency = self.env['res.currency'].browse(g['currency_id'][0])
                    total += currency._convert(
                        g['amount_total'],
                        company_currency,
                        self.env.company,
                        today
                    )
            return total

        total_revenue_mtd = _get_total(month_start)
        total_revenue_ytd = _get_total(year_start)

        groups = SaleOrder.read_group(
            [('state', '=', 'sale')],
            ['amount_total:sum', 'id:count'],
            ['currency_id']
        )

        total_revenue = 0.0
        total_orders = 0
        for g in groups:
            if g['currency_id']:
                currency = self.env['res.currency'].browse(g['currency_id'][0])
                total_revenue += currency._convert(
                    g['amount_total'],
                    company_currency,
                    self.env.company,
                    today
                )
                total_orders += g.get('currency_id_count', 0)

        avg_order_value = total_revenue / total_orders if total_orders else 0

        sales_info = {
            'sale_orders': sale_orders,
            'quotation': quotations,
            'orders_to_invoice': orders_to_invoice,
            'orders_fully_invoiced': orders_fully_invoiced,
            'conversion_rate': conversion_rate,
            'total_revenue_mtd': company_currency.format(total_revenue_mtd),
            'total_revenue_ytd': company_currency.format(total_revenue_ytd),
            'avg_order_value': company_currency.format(avg_order_value),
        }

        nvrc_domain = build_domain([('state', 'in', ['sale', 'done'])], "nvrc_filter")

        date_from, date_to = None, None
        for d in nvrc_domain:
            if d[0] == 'date_order' and d[1] == '>=':
                date_from = d[2]
            elif d[0] == 'date_order' and d[1] == '<=':
                date_to = d[2]

        if date_from and isinstance(date_from, str):
            date_from = fields.Date.from_string(date_from)
        if date_to and isinstance(date_to, str):
            date_to = fields.Date.from_string(date_to)

        current_customers = self.read_group(
            nvrc_domain, ['partner_id'], ['partner_id']
        )
        customer_ids = [rec['partner_id'][0] for rec in current_customers if rec['partner_id']]

        new_customers, returning_customers = [], []
        if customer_ids:
            first_orders = self.read_group(
                [('partner_id', 'in', customer_ids), ('state', 'in', ['sale', 'done'])],
                ['partner_id', 'date_order:min'],
                ['partner_id']
            )
            first_order_map = {rec['partner_id'][0]: rec['date_order'] for rec in first_orders if rec['partner_id']}

            partners = self.env['res.partner'].browse(customer_ids)
            for partner in partners:
                first_date = first_order_map.get(partner.id)
                if first_date and date_from and first_date.date() >= date_from:
                    new_customers.append({'id': partner.id, 'name': partner.display_name})
                else:
                    returning_customers.append({'id': partner.id, 'name': partner.display_name})

        new_vs_returning = {
            'summary': {
                'labels': [_("New Customers"), _("Returning Customers")],
                'values': [len(new_customers), len(returning_customers)],
            },
            'details': {
                'new': new_customers[:limit],
                'returning': returning_customers[:limit],
            }
        }

        # ── Project metrics ──────────────────────────────────────────────────

        project_year_filter = filters.get("project_year_filter")
        all_projects = self.env['xinxu.project'].search([])

        projects_per_year = {}
        for proj in all_projects:
            yr = str(proj.year)
            projects_per_year[yr] = projects_per_year.get(yr, 0) + 1

        projects_per_year_list = [
            {'year': yr, 'count': cnt}
            for yr, cnt in sorted(projects_per_year.items(), reverse=True)
        ]

        project_domain = [
            ('state', 'in', ['sale', 'done']),
            ('xinxu_project_id', '!=', False),
        ]
        if project_year_filter:
            project_domain.append(('xinxu_project_id.year', '=', int(project_year_filter)))

        revenue_groups = self.read_group(
            project_domain,
            ['amount_total', 'currency_id'],
            ['xinxu_project_id', 'currency_id'],
            lazy=False,
        )

        project_revenue_map = {}
        for g in revenue_groups:
            if not g.get('xinxu_project_id'):
                continue
            proj_id, proj_name = g['xinxu_project_id']
            currency_id = g['currency_id'][0] if g['currency_id'] else False
            amount = g.get('amount_total', 0.0)
            if currency_id:
                currency = self.env['res.currency'].browse(currency_id)
                amount = currency._convert(amount, company_currency, self.env.company, today)
            if proj_id not in project_revenue_map:
                project_revenue_map[proj_id] = {'id': proj_id, 'name': proj_name, 'revenue': 0.0}
            project_revenue_map[proj_id]['revenue'] += amount

        revenue_per_project = sorted(
            project_revenue_map.values(), key=lambda x: x['revenue'], reverse=True
        )
        for item in revenue_per_project:
            item['revenue'] = company_currency.format(item['revenue'])

        person_project_domain = [
            ('state', 'in', ['sale', 'done']),
            ('xinxu_project_id', '!=', False),
        ]
        if project_year_filter:
            person_project_domain.append(('xinxu_project_id.year', '=', int(project_year_filter)))

        person_project_groups = self.read_group(
            person_project_domain,
            ['amount_total', 'currency_id'],
            ['xinxu_project_id', 'user_id', 'currency_id'],
            lazy=False,
        )

        proj_person_totals = {}
        for g in person_project_groups:
            if not g.get('xinxu_project_id') or not g.get('user_id'):
                continue
            proj_id, proj_name = g['xinxu_project_id']
            user_id, user_name = g['user_id']
            currency_id = g['currency_id'][0] if g['currency_id'] else False
            amount = g.get('amount_total', 0.0)
            if currency_id:
                currency = self.env['res.currency'].browse(currency_id)
                amount = currency._convert(amount, company_currency, self.env.company, today)

            if proj_id not in proj_person_totals:
                proj_person_totals[proj_id] = {'name': proj_name, 'persons': {}}
            proj_person_totals[proj_id]['persons'].setdefault(user_id, {'name': user_name, 'total': 0.0})
            proj_person_totals[proj_id]['persons'][user_id]['total'] += amount

        avg_revenue_per_person = []
        for proj_id, data in proj_person_totals.items():
            persons_list = list(data['persons'].values())
            avg = sum(p['total'] for p in persons_list) / len(persons_list) if persons_list else 0.0
            avg_revenue_per_person.append({
                'id': proj_id,
                'project': data['name'],
                'avg_per_person': company_currency.format(avg),
                'persons': [
                    {'name': p['name'], 'revenue': company_currency.format(p['total'])}
                    for p in persons_list
                ],
            })

        available_years = sorted(
            {str(p.year) for p in all_projects}, reverse=True
        )

        return {
            'sales_by_team': teams,
            'sales_by_person': persons,
            'top_customers': customers,
            'top_products': top_products,
            'lowest_products': low_products,
            'overdue_customers': overdue_customers,
            'order_status': order_status,
            'invoice_status': invoice_status,
            'product_categories': product_categories,
            'sales_info': sales_info,
            'new_vs_returning': new_vs_returning,
            'projects_per_year': projects_per_year_list,
            'revenue_per_project': revenue_per_project,
            'avg_revenue_per_person': avg_revenue_per_person,
            'project_available_years': available_years,
        }
