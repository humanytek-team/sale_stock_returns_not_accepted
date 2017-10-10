# -*- coding: utf-8 -*-
# Copyright 2017 Humanytek - Manuel Marquez <manuel@humanytek.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import api, fields, models
from openerp.tools.translate import _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_add_returns_not_accepted(self):
        """Process action of button 'Add returns not accepted'"""

        StockQuant = self.env['stock.quant']
        StockLocation = self.env['stock.location']
        so_warehouse_company_id = self.warehouse_id.company_id.id
        returns_not_accepted_locations = StockLocation.search([
            ('company_id', '=', so_warehouse_company_id),
            ('return_not_accepted_location', '=', True),
        ])

        if returns_not_accepted_locations:
            customer_quants = StockQuant.search([
                ('history_ids.partner_id', '=', self.partner_id.id),
                ('location_id', 'in', returns_not_accepted_locations.mapped('id')),
                ])

            if customer_quants:
                customer_products_returned_not_accepted = dict()

                for quant in customer_quants:
                    quant_last_move = quant.history_ids.filtered(
                        lambda sm: sm.location_dest_id.id in
                        returns_not_accepted_locations.mapped('id')).sorted(
                            key=lambda sm: sm.date)[-1]

                    if quant_last_move.partner_id == self.partner_id:
                        if str(quant_last_move.product_id.id) not in \
                            customer_products_returned_not_accepted:

                            customer_products_returned_not_accepted[
                                str(quant_last_move.product_id.id)] = \
                                    quant_last_move.product_uom_qty

                        else:
                            customer_products_returned_not_accepted[
                                str(quant_last_move.product_id.id)] += \
                                    quant_last_move.product_uom_qty

                Product = self.env['product.product']
                SaleOrderLine = self.env['sale.order.line']

                for product_id in customer_products_returned_not_accepted:
                    product_in_another_order = SaleOrderLine.search([
                        ('order_id', '!=', self.id),
                        ('order_id.state', '=', 'sale'),
                        ('product_id', '=', int(product_id)),
                        ('return_not_accepted', '=', True),
                    ])

                    if not product_in_another_order:

                        if not any(
                                line.product_id.id == int(product_id) and
                                line.return_not_accepted
                                for line in self.order_line):

                            product = Product.browse(int(product_id))
                            so_line = dict()
                            so_line['product_id'] = int(product_id)
                            so_line['product_uom_qty'] = \
                                customer_products_returned_not_accepted[
                                    product_id]
                            so_line['name'] = '%s: %s' % (
                                _('[RETURN]'), product.display_name)
                            so_line['price_unit'] = 0
                            so_line['return_not_accepted'] = True
                            self.update({'order_line': [(0, 0, so_line)]})

                        else:
                            product_order_line = self.order_line.filtered(
                                lambda line: line.product_id.id == int(
                                    product_id) and line.return_not_accepted
                            )

                            product_qty_order = sum(
                                product_order_line.mapped('product_uom_qty')
                                )

                            if product_qty_order < \
                                customer_products_returned_not_accepted[
                                        product_id]:

                                product_remaining_qty = \
                                    customer_products_returned_not_accepted[
                                        product_id
                                    ] - \
                                    product_qty_order

                                product_order_line[0].product_uom_qty += \
                                    product_remaining_qty

                    else:

                        product_another_order_total_qty = \
                            sum(
                                product_in_another_order.mapped(
                                    'product_uom_qty')
                                )

                        if product_another_order_total_qty < \
                            customer_products_returned_not_accepted[product_id]:

                            product_qty = \
                                customer_products_returned_not_accepted[
                                    product_id
                                ] - product_another_order_total_qty

                            if not any(
                                    line.product_id.id == int(product_id) and
                                    line.return_not_accepted
                                    for line in self.order_line):

                                product = Product.browse(int(product_id))
                                so_line = dict()
                                so_line['product_id'] = int(product_id)
                                so_line['product_uom_qty'] = product_qty
                                so_line['name'] = '%s: %s' % (
                                    _('[RETURN]'), product.display_name)
                                so_line['price_unit'] = 0
                                so_line['return_not_accepted'] = True
                                self.update({'order_line': [(0, 0, so_line)]})

                            else:
                                product_order_line = self.order_line.filtered(
                                    lambda line: line.product_id.id == int(
                                        product_id) and line.return_not_accepted
                                )

                                product_qty_order = sum(
                                    product_order_line.mapped('product_uom_qty')
                                    )

                                if product_qty_order < product_qty:
                                    product_remaining_qty = product_qty - \
                                        product_qty_order

                                    product_order_line[0].product_uom_qty += \
                                        product_remaining_qty


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    return_not_accepted = fields.Boolean('Is return not accepted ?')
