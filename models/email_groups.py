# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EmailGroups(models.Model):
    _name = 'amgl.email.group'
    _description = 'Email Groups'
    _sql_constraints = [
        ('uniq_name', 'unique(name)', 'Email Group with same name already exists!'),
    ]

    @api.model
    def create(self, vals):
        if vals['name']:
            current_object_name = vals['name'].lstrip(' ').rstrip(' ')
            custodians = self.env['amgl.email.group'].search([])
            self.validate_email_group_name(custodians, current_object_name)

        if vals['emails']:
            current_object_email = vals['emails'].lstrip(' ').rstrip(' ')
            email_groups = self.env['amgl.email.group'].search([])
            self.validate_email(email_groups, current_object_email)

        record = super(EmailGroups, self).create(vals)
        return record

    @staticmethod
    def validate_email_group_name(email_groups,current_obj_name):
        if len(email_groups) > 0:
            for email_group in email_groups:
                if email_group.name.lower() == current_obj_name.lower():
                    raise ValidationError('Email Group with same name already exists!')

    @staticmethod
    def validate_email(email_groups, current_obj_name):
        if len(email_groups) > 0:
            for email_group in email_groups:
                if email_group.name.lower() == current_obj_name.lower():
                    raise ValidationError('Email already exists in other group!')

    name = fields.Char(string='Email Group Name', required=True)
    emails= fields.Char(string='Group Emails', required=True)
    notification = fields.Char(default='Multiple emails should be comma separated', readonly=True)
