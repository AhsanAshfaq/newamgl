# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PossibleReasons(models.Model):
    _name = 'amgl.possible_reason'
    _description = 'Possible Reasons'

    name = fields.Char(required=True)
    possible_solutions = fields.One2many('amgl.possible_solution', 'reason_id', string="Possible Reason")