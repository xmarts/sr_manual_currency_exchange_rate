# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.float_utils import float_round, float_is_zero
import dateutil.parser


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_price_unit(self):
        """ Returns the unit price for the move"""
        self.ensure_one()
        if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
            price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
            line = self.purchase_line_id
            order = line.order_id
            price_unit = line.price_unit
            if line.taxes_id:
                qty = line.product_qty or 1
                price_unit = line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id, quantity=qty)['total_void']
                price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
            if line.product_uom.id != line.product_id.uom_id.id:
                price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
            if order.currency_id != order.company_id.currency_id:
                # The date must be today, and not the date of the move since the move move is still
                # in assigned state. However, the move date is the scheduled date until move is
                # done, then date of actual move processing. See:
                # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
                date_order = str(order.date_order).split(' ')[0]
                date_order = dateutil.parser.parse(date_order).date()
                icp = self.env['ir.config_parameter'].sudo()
                take_exchange_rate_from_purchase_order = icp.get_param('inventory_valuation_by_date_of_purchase.take_exchange_rate_from_purchase_order')
                if take_exchange_rate_from_purchase_order:
                    if order.apply_manual_currency_exchange:
                        price_unit = price_unit * (1.0 / order.manual_currency_exchange_rate)
                    else:
                        price_unit = order.currency_id._convert(
                            price_unit, order.company_id.currency_id,
                            order.company_id, date_order, round=False)
                else:
                    price_unit = order.currency_id._convert(
                        price_unit, order.company_id.currency_id,
                        order.company_id, fields.Date.context_today(self),
                        round=False)
            return price_unit
        return super(StockMove, self)._get_price_unit()
