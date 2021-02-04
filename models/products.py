# -*- coding: utf-8 -*-

import string

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Products(models.Model):
    _name = 'amgl.products'
    _description = 'Product'
    _rec_name = 'goldstar_name'
    _sql_constraints = [
        ('uniq_product_code', 'unique(product_code)', 'Product_code already exists!')
    ]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        text = string.replace(name, ' ', '%')
        name = '%' + text + '%'
        domain = [('product_code', operator, name)]
        products = self.search(domain + args, limit=limit)
        return products.name_get()

    @api.model
    def create(self, vals):
        weight_per_price = vals.get('weight_per_piece')
        if weight_per_price and weight_per_price == '0':
            raise ValidationError("Weight per price must be greater than 0.")
        record = super(Products, self).create(vals)
        return record

    @api.multi
    def write(self, vals):
        weight_per_price = vals.get('weight_per_piece')
        if weight_per_price and weight_per_price == '0':
            raise ValidationError("Weight per price must be greater than 0.")
        record = super(Products, self).write(vals)
        return record

    name = fields.Char('Amark Description', required=True)
    goldstar_name = fields.Char('GoldStar Description', required=True)
    type = fields.Selection(
        selection=[('Gold', 'Gold'), ('Silver', 'Silver')
            , ('Platinum', 'Platinum'), ('Palladium', 'Palladium')]
        , string="Commodity", required=True)
    weight_per_piece = fields.Float(string="Weight Per Piece", required=True)
    weight_unit = fields.Selection(string="Weight Unit", selection=[('oz', 'Ounce'), ('gram', 'Gram')
            , ('kg', 'Kilogram'), ('pounds', 'Pounds')], required=True, default="oz")
    customer_ids = fields.Many2many('amgl.customer', string='Customers')
    product_code = fields.Char(string="Product Code", required=True)
    gs_product_code = fields.Char(string="GoldStar Product Code", required=True)
