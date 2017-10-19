# -*- coding: utf-8 -*-
# Copyright 2017 Humanytek - Manuel Marquez <manuel@humanytek.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from openerp import api, fields, models
from openerp.exceptions import UserError
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
                                str(quant_last_move.product_id.id)] = [{
                                    'location_id': \
                                        quant_last_move.location_dest_id.id,
                                    'qty': quant.qty,
                                    }]

                        else:
                            customer_products_not_accepted_locations = [
                                location_products['location_id']
                                for location_products in
                                customer_products_returned_not_accepted[
                                    str(quant_last_move.product_id.id)
                                ]
                            ]

                            if quant_last_move.location_dest_id.id in \
                                customer_products_not_accepted_locations:

                                for location_products in \
                                    customer_products_returned_not_accepted[
                                        str(quant_last_move.product_id.id)]:

                                    if location_products['location_id'] == \
                                        quant_last_move.location_dest_id.id:

                                        location_products['qty'] += \
                                            quant.qty

                            else:
                                customer_products_returned_not_accepted[
                                    str(quant_last_move.product_id.id)].append({
                                        'location_id': quant_last_move.location_dest_id,
                                        'qty': quant.qty,
                                        })


                Product = self.env['product.product']
                SaleOrderLine = self.env['sale.order.line']

                if not customer_products_returned_not_accepted:
                    raise UserError(_('No returns found for this customer'))

                for product_id in customer_products_returned_not_accepted:
                    product_in_another_order = SaleOrderLine.search([
                        ('order_id', '!=', self.id),
                        ('order_id.state', '=', 'sale'),
                        ('product_id', '=', int(product_id)),
                        ('return_not_accepted', '=', True),
                        ('product_uom_qty', '>', 0),
                        ('partner_id', '=', self.partner_id.id),
                    ])

                    total_product_qty = sum([
                        location_products['qty']
                        for location_products in
                        customer_products_returned_not_accepted[
                            product_id
                            ]
                        ])


                    if not product_in_another_order:

                        if not any(
                                line.product_id.id == int(product_id) and
                                line.return_not_accepted
                                for line in self.order_line):

                            product = Product.browse(int(product_id))
                            so_line = dict()
                            so_line['product_id'] = int(product_id)
                            so_line['product_uom_qty'] = total_product_qty
                            so_line['name'] = '%s: %s' % (
                                _('[RETURN]'), product.display_name)
                            so_line['price_unit'] = 0
                            so_line['return_not_accepted'] = True
                            self.update({'order_line': [(0, 0, so_line)]})

                            for picking in self.picking_ids:
                                for move in picking.move_lines_related:
                                    sale_order_line = \
                                        move.procurement_id.sale_line_id

                                    if move.product_id.id == int(product_id)\
                                            and sale_order_line.return_not_accepted:

                                        first_location = StockLocation.browse(
                                            customer_products_returned_not_accepted[
                                                product_id
                                            ][0]['location_id']
                                        )

                                        if len(
                                            customer_products_returned_not_accepted[
                                                product_id
                                            ]) == 1:

                                            move.location_id = first_location

                                        else:

                                            move.location_id = first_location
                                            for i in range(1, len(customer_products_returned_not_accepted[
                                                product_id
                                            ])):

                                                move.copy({
                                                    'location_id': customer_products_returned_not_accepted[
                                                        product_id][i]['location_id'],
                                                    'product_uom_qty': customer_products_returned_not_accepted[
                                                        product_id][i]['qty'],
                                                    })

                                for op in picking.pack_operation_product_ids:
                                    if op.product_id.id == int(product_id):
                                        if op.product_qty > total_product_qty:
                                            op.product_qty -= total_product_qty

                                            for location_products in \
                                                customer_products_returned_not_accepted[
                                                        product_id]:

                                                op.copy({
                                                    'location_id': location_products[
                                                        'location_id'],
                                                    'product_qty': location_products[
                                                        'qty'],
                                                    })

                                        else:

                                            op_location = StockLocation.browse(
                                                customer_products_returned_not_accepted[
                                                    product_id][0][
                                                        'location_id'])

                                            op.location_id = op_location

                                            if len(
                                                customer_products_returned_not_accepted[
                                                    product_id]
                                                ) > 1:

                                                first_location_product_qty = StockLocation.browse(
                                                    customer_products_returned_not_accepted[
                                                        product_id][0][
                                                            'qty'])
                                                op.product_qty = first_location_product_qty

                                                for i in range(1, len(customer_products_returned_not_accepted[
                                                    product_id
                                                ])):

                                                    op.copy({
                                                        'location_id': customer_products_returned_not_accepted[
                                                            product_id][i]['location_id'],
                                                        'product_qty': customer_products_returned_not_accepted[
                                                            product_id][i]['qty'],
                                                        })

                        else:
                            product_order_line = self.order_line.filtered(
                                lambda line: line.product_id.id == int(
                                    product_id) and line.return_not_accepted
                            )

                            product_qty_order = sum(
                                product_order_line.mapped('product_uom_qty')
                                )

                            if product_qty_order < \
                                total_product_qty:

                                product_remaining_qty = \
                                    total_product_qty - product_qty_order

                                product_order_line[0].product_uom_qty += \
                                    product_remaining_qty

                                for picking in self.picking_ids:
                                    for move in picking.move_lines_related:
                                        sale_order_line = \
                                            move.procurement_id.sale_line_id

                                        if move.product_id.id == int(product_id)\
                                                and sale_order_line.return_not_accepted:

                                            first_location = StockLocation.browse(
                                                customer_products_returned_not_accepted[
                                                    product_id
                                                ][0]['location_id']
                                            )

                                            if len(
                                                customer_products_returned_not_accepted[
                                                    product_id
                                                ]) == 1:

                                                move.location_id = first_location

                                            else:

                                                move.location_id = first_location
                                                for i in range(1, len(customer_products_returned_not_accepted[
                                                    product_id
                                                ])):

                                                    move.copy({
                                                        'location_id': customer_products_returned_not_accepted[
                                                            product_id][i]['location_id'],
                                                        'product_uom_qty': customer_products_returned_not_accepted[
                                                            product_id][i]['qty'],
                                                        })

                                    for op in picking.pack_operation_product_ids:
                                        if op.product_id.id == int(product_id):
                                            if op.product_qty > total_product_qty:
                                                op.product_qty -= total_product_qty

                                                for location_products in \
                                                    customer_products_returned_not_accepted[
                                                            product_id]:

                                                    op.copy({
                                                        'location_id': location_products[
                                                            'location_id'],
                                                        'product_qty': location_products[
                                                            'qty'],
                                                        })

                                            else:

                                                op_location = StockLocation.browse(
                                                    customer_products_returned_not_accepted[
                                                        product_id][0][
                                                            'location_id'])

                                                op.location_id = op_location

                                                if len(
                                                    customer_products_returned_not_accepted[
                                                        product_id]
                                                    ) > 1:

                                                    first_location_product_qty = StockLocation.browse(
                                                        customer_products_returned_not_accepted[
                                                            product_id][0][
                                                                'qty'])
                                                    op.product_qty = first_location_product_qty

                                                    for i in range(1, len(customer_products_returned_not_accepted[
                                                        product_id
                                                    ])):

                                                        op.copy({
                                                            'location_id': customer_products_returned_not_accepted[
                                                                product_id][i]['location_id'],
                                                            'product_qty': customer_products_returned_not_accepted[
                                                                product_id][i]['qty'],
                                                            })

                            else:
                                raise UserError(_('The products has been added to this sale order'))

                    else:

                        product_another_order_total_qty = \
                            sum(
                                product_in_another_order.mapped(
                                    'product_uom_qty')
                                )

                        if product_another_order_total_qty < total_product_qty:

                            product_qty = \
                                total_product_qty - \
                                    product_another_order_total_qty

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

                                for picking in self.picking_ids:
                                    for move in picking.move_lines_related:
                                        sale_order_line = \
                                            move.procurement_id.sale_line_id

                                        if move.product_id.id == int(product_id)\
                                                and sale_order_line.return_not_accepted:

                                            first_location = StockLocation.browse(
                                                customer_products_returned_not_accepted[
                                                    product_id
                                                ][0]['location_id']
                                            )

                                            if len(
                                                customer_products_returned_not_accepted[
                                                    product_id
                                                ]) == 1:

                                                move.location_id = first_location

                                            else:

                                                move.location_id = first_location
                                                for i in range(1, len(customer_products_returned_not_accepted[
                                                    product_id
                                                ])):

                                                    move.copy({
                                                        'location_id': customer_products_returned_not_accepted[
                                                            product_id][i]['location_id'],
                                                        'product_uom_qty': customer_products_returned_not_accepted[
                                                            product_id][i]['qty'],
                                                        })

                                    for op in picking.pack_operation_product_ids:
                                        if op.product_id.id == int(product_id):
                                            if op.product_qty > total_product_qty:
                                                op.product_qty -= total_product_qty

                                                for location_products in \
                                                    customer_products_returned_not_accepted[
                                                            product_id]:

                                                    op.copy({
                                                        'location_id': location_products[
                                                            'location_id'],
                                                        'product_qty': location_products[
                                                            'qty'],
                                                        })

                                            else:

                                                op_location = StockLocation.browse(
                                                    customer_products_returned_not_accepted[
                                                        product_id][0][
                                                            'location_id'])

                                                op.location_id = op_location

                                                if len(
                                                    customer_products_returned_not_accepted[
                                                        product_id]
                                                    ) > 1:

                                                    first_location_product_qty = StockLocation.browse(
                                                        customer_products_returned_not_accepted[
                                                            product_id][0][
                                                                'qty'])
                                                    op.product_qty = first_location_product_qty

                                                    for i in range(1, len(customer_products_returned_not_accepted[
                                                        product_id
                                                    ])):

                                                        op.copy({
                                                            'location_id': customer_products_returned_not_accepted[
                                                                product_id][i]['location_id'],
                                                            'product_qty': customer_products_returned_not_accepted[
                                                                product_id][i]['qty'],
                                                            })

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

                                    for picking in self.picking_ids:
                                        for move in picking.move_lines_related:
                                            sale_order_line = \
                                                move.procurement_id.sale_line_id

                                            if move.product_id.id == int(product_id)\
                                                    and sale_order_line.return_not_accepted:

                                                first_location = StockLocation.browse(
                                                    customer_products_returned_not_accepted[
                                                        product_id
                                                    ][0]['location_id']
                                                )

                                                if len(
                                                    customer_products_returned_not_accepted[
                                                        product_id
                                                    ]) == 1:

                                                    move.location_id = first_location

                                                else:

                                                    move.location_id = first_location
                                                    for i in range(1, len(customer_products_returned_not_accepted[
                                                        product_id
                                                    ])):

                                                        move.copy({
                                                            'location_id': customer_products_returned_not_accepted[
                                                                product_id][i]['location_id'],
                                                            'product_uom_qty': customer_products_returned_not_accepted[
                                                                product_id][i]['qty'],
                                                            })

                                        for op in picking.pack_operation_product_ids:
                                            if op.product_id.id == int(product_id):
                                                if op.product_qty > total_product_qty:
                                                    op.product_qty -= total_product_qty

                                                    for location_products in \
                                                        customer_products_returned_not_accepted[
                                                                product_id]:

                                                        op.copy({
                                                            'location_id': location_products[
                                                                'location_id'],
                                                            'product_qty': location_products[
                                                                'qty'],
                                                            })

                                                else:

                                                    op_location = StockLocation.browse(
                                                        customer_products_returned_not_accepted[
                                                            product_id][0][
                                                                'location_id'])

                                                    op.location_id = op_location

                                                    if len(
                                                        customer_products_returned_not_accepted[
                                                            product_id]
                                                        ) > 1:

                                                        first_location_product_qty = StockLocation.browse(
                                                            customer_products_returned_not_accepted[
                                                                product_id][0][
                                                                    'qty'])
                                                        op.product_qty = first_location_product_qty

                                                        for i in range(1, len(customer_products_returned_not_accepted[
                                                            product_id
                                                        ])):

                                                            op.copy({
                                                                'location_id': customer_products_returned_not_accepted[
                                                                    product_id][i]['location_id'],
                                                                'product_qty': customer_products_returned_not_accepted[
                                                                    product_id][i]['qty'],
                                                                })

                                else:
                                    raise UserError(_('The products has been added to this sale order'))

                        else:
                            raise UserError(_('The products has been added in other sale order(s)'))

            else:
                raise UserError(_('No returns found for this customer'))

        else:
            raise UserError(_('No has been found a location of returns not accepted for your company.'))


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    return_not_accepted = fields.Boolean('Is return not accepted ?')
