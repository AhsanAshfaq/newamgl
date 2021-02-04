# -*- coding: utf-8 -*-

from odoo import models, fields, api


class OrderHistory(models.Model):
    _name = 'amgl.order.history'
    _description = 'Order History'

    name = fields.Char()
    date_create = fields.Datetime()
    fields_updated = fields.Char()
    remaining_quantity = fields.Float()
    received_quantity = fields.Float()
    orderline_id = fields.Many2one('amgl.order_line',string="Order Lines")
    updated_by = fields.Many2one('res.users')
