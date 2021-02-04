# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class EmailTypeGroupAssociation(models.Model):
    _name = 'amgl.email.type.group.association'
    _description = 'AMGL Metal Closing Rates'

    def get_email_type(self):
        return [('IRA Approval Needed', 'IRA Approval Needed'), ('Revised Approval Needed', 'Revised Approval Needed')]



    email_type = fields.Selection(selection=get_email_type, required=True)

