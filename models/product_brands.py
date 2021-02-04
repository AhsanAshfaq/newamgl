# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductBrands(models.Model):
    _name = 'amgl.product.brands'
    _description = 'Product Brands'
    _sql_constraints = [
        ('uniq_name', 'unique(name)', 'Brand with same name already exists!'),
    ]

    @api.model
    def create(self, vals):
        if vals['name']:
            current_object_name = vals['name'].lstrip(' ').rstrip(' ')
            brands = self.env['amgl.product.brands'].search([])
            self.validate_brand(brands,current_object_name)
            record = super(ProductBrands, self).create(vals)
            return record

    @staticmethod
    def validate_brand(brands,current_obj_name):
        if len(brands) > 0:
            for brand in brands:
                if brand.name.lower() == current_obj_name.lower():
                    raise ValidationError('Brand with same name already exists!')

    name = fields.Char('Brand')
