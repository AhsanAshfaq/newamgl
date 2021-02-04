# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api


class PendingAccounts(models.Model):
    _name = 'amgl.pending.accounts'
    _description = 'Pending Account'

    @api.multi
    @api.depends('quantity_expected','quantity_received')
    def _calculate_remaining_products(self):
        qty = 0
        for p in self:
            qty = p.quantity_expected-p.quantity_received
            p.update({
                'remaining_products':qty
            })
        return qty

    name = fields.Char()
    first_name = fields.Char(string="First Name")
    last_name = fields.Char(string="Last Name")
    quantity_expected = fields.Float(string="Quantity Expected")
    quantity_received = fields.Float(string="Quantity Received")
    possible_reason = fields.Many2one('amgl.possible_reason', string='Possible Reason')
    possible_solution = fields.Many2one('amgl.possible_solution', string='Possible Solution')
    notes = fields.Html(string='Notes')
    date_received = fields.Datetime(string="Received Date")
    remaining_products = fields.Float(string="Remaining Products", compute="_calculate_remaining_products")
    order_line_id = fields.Integer(string='order_line_id')
