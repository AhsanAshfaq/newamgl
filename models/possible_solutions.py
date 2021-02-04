# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PossibleSolutions(models.Model):
    _name = 'amgl.possible_solution'
    _description = 'Possible Solution'

    name = fields.Char(required=True)
    reason_id = fields.Many2one('amgl.possible_reason',string="Possible Reason",required=True)
