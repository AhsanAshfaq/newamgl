from odoo import fields, models, api
from odoo.exceptions import ValidationError


class UserExtension(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    custodian_id = fields.Many2one('amgl.custodian', string='Custodian ID')

    @api.model
    def create(self, values):
        if values:
            if values['in_group_12'] and not values['custodian_id']:
                raise ValidationError("Please select parent custodian")
        user = super(UserExtension, self).create(values)
        return user


    @api.multi
    def write(self, vals):
        if vals:
            if (vals.get('in_group_12') is not None and vals.get('in_group_12')) and \
                    (vals.get('custodian_id') is None or not vals.get('custodian_id')):
                raise ValidationError("Please select parent custodian")
        user = super(UserExtension, self).write(vals)
        return user
