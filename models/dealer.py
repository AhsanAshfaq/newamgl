# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Dealer(models.Model):
    _name = 'amgl.dealer'
    _description = 'Dealer'

    name = fields.Char()
    customer_ids = fields.Many2many('amgl.customer', string='Customers')
