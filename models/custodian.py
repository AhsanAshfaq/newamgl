# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Custodian(models.Model):
    _name = 'amgl.custodian'
    _description = 'Custodian'
    _sql_constraints = [
        ('uniq_name', 'unique(name)', 'Custodian with same name already exists!'),
    ]

    @api.model
    def create(self, vals):
        if vals['name']:
            current_object_name = vals['name'].lstrip(' ').rstrip(' ')
            custodians = self.env['amgl.custodian'].search([])
            self.validate_custodian(custodians,current_object_name)
            record = super(Custodian, self).create(vals)
            return record

    @staticmethod
    def validate_custodian(custodians,current_obj_name):
        if len(custodians) > 0:
            for custodian in custodians:
                if custodian.name.lower() == current_obj_name.lower():
                    raise ValidationError('Custodian with same name already exists!')

    name = fields.Char('Custodian')
    custodian_code = fields.Char('Code')
